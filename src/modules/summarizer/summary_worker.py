"""SummaryWorker — Worker thread cho quá trình tổng hợp tài liệu."""

import logging
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.core.config import ConfigManager
from src.processors.base import ExtractedContent
from src.providers.base import BaseProvider
from src.providers.token_counter import estimate_tokens

logger = logging.getLogger(__name__)

# Retry config (giống ai_engine.py)
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0

_RETRYABLE_KEYWORDS = (
    "timeout", "timed out", "connection", "reset by peer",
    "rate limit", "too many requests", "overloaded", "unavailable",
    "503", "502", "504", "429",
)


def _is_retryable(e: Exception) -> bool:
    """Kiểm tra lỗi có thể retry không."""
    s = str(e).lower()
    return any(kw in s for kw in _RETRYABLE_KEYWORDS)


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Báo cáo tổng hợp - LazyDoc</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true, theme:'neutral', securityLevel:'loose'}});</script>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 960px; margin: 40px auto; padding: 0 24px; color: #24273a; line-height: 1.7; background: #eff1f5; }}
  h1 {{ color: #1e66f5; border-bottom: 3px solid #1e66f5; padding-bottom: 8px; }}
  h2 {{ color: #179299; margin-top: 36px; border-left: 4px solid #179299; padding-left: 12px; }}
  h3 {{ color: #8839ef; margin-top: 24px; }}
  hr {{ border: none; border-top: 1px solid #ccd0da; margin: 24px 0; }}
  ul {{ padding-left: 20px; }}
  li {{ margin: 4px 0; }}
  ul.checklist {{ list-style: none; padding-left: 4px; }}
  ul.checklist li {{ display: flex; align-items: flex-start; gap: 8px; }}
  strong {{ color: #d20f39; }}
  pre {{ background: #e6e9ef; border-radius: 8px; padding: 12px 16px; overflow-x: auto; }}
  code {{ background: #ccd0da; border-radius: 4px; padding: 1px 5px; font-family: monospace; font-size: 0.9em; }}
  pre code {{ background: none; padding: 0; }}
  .mermaid {{ background: #fff; border-radius: 10px; padding: 20px; margin: 20px 0; overflow-x: auto; border: 1px solid #ccd0da; text-align: center; }}
  .qa-section {{ margin-top: 48px; border-top: 3px solid #fe640b; padding-top: 24px; }}
  .qa-section h2 {{ color: #fe640b; border-left-color: #fe640b; }}
  .qa-q {{ background: #e6e9ef; border-radius: 8px; padding: 10px 16px; margin: 16px 0 4px; font-weight: bold; }}
  .qa-q::before {{ content: "❓ "; }}
  .qa-a {{ background: #fff; border-radius: 8px; padding: 10px 16px; margin: 0 0 16px; border-left: 3px solid #179299; white-space: pre-wrap; }}
</style>
</head>
<body>
<div class="container">
{body}
</div>
</body>
</html>"""


def _md_to_html(md_text: str, qa_history: list[tuple[str, str]] | None = None) -> str:
    """Chuyển đổi Markdown sang HTML có style, hỗ trợ Mermaid diagram.

    Mermaid code block (```mermaid) được render thành <div class="mermaid">
    để Mermaid.js CDN xử lý khi mở file trong browser.

    Args:
        md_text: Nội dung Markdown (có thể chứa mermaid blocks).
        qa_history: Danh sách [(câu_hỏi, câu_trả_lời)] để thêm vào cuối.

    Returns:
        HTML đầy đủ với DOCTYPE, styling, và Mermaid.js CDN.
    """
    import html as html_lib
    import re

    def inline(text: str) -> str:
        text = html_lib.escape(text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        return text

    lines = md_text.split("\n")
    parts: list[str] = []
    in_ul = False
    ul_is_checklist = False
    para_lines: list[str] = []
    in_code_block = False
    code_lang = ""
    code_lines: list[str] = []

    def flush_para() -> None:
        if para_lines:
            parts.append(f"<p>{'<br>'.join(para_lines)}</p>")
            para_lines.clear()

    def close_ul() -> None:
        nonlocal in_ul, ul_is_checklist
        if in_ul:
            parts.append("</ul>")
            in_ul = False
            ul_is_checklist = False

    def flush_code_block() -> None:
        content = "\n".join(code_lines)
        if code_lang == "mermaid":
            # Không escape — Mermaid.js cần raw text
            parts.append(f'<div class="mermaid">{content}</div>')
        else:
            escaped = html_lib.escape(content)
            lang_class = f' class="language-{code_lang}"' if code_lang else ""
            parts.append(f"<pre><code{lang_class}>{escaped}</code></pre>")

    for line in lines:
        stripped = line.strip()

        # --- Xử lý fenced code block ---
        if in_code_block:
            if stripped == "```":
                flush_code_block()
                in_code_block = False
                code_lang = ""
                code_lines = []
            else:
                code_lines.append(line)
            continue

        if stripped.startswith("```"):
            close_ul(); flush_para()
            code_lang = stripped[3:].strip().lower()
            in_code_block = True
            code_lines = []
            continue

        # --- Xử lý markdown thông thường ---
        if stripped.startswith("# "):
            close_ul(); flush_para()
            parts.append(f"<h1>{inline(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            close_ul(); flush_para()
            parts.append(f"<h2>{inline(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            close_ul(); flush_para()
            parts.append(f"<h3>{inline(stripped[4:])}</h3>")
        elif stripped.startswith("#### "):
            close_ul(); flush_para()
            parts.append(f"<h4>{inline(stripped[5:])}</h4>")
        elif stripped == "---":
            close_ul(); flush_para()
            parts.append("<hr>")
        elif re.match(r'^-\s*\[[ xX]\]', stripped):
            flush_para()
            checked = "checked" if stripped[3] in ("x", "X") else ""
            text = inline(re.sub(r'^-\s*\[[ xX]\]\s*', "", stripped))
            if not in_ul:
                parts.append('<ul class="checklist">')
                in_ul = True
                ul_is_checklist = True
            parts.append(f'<li><input type="checkbox" {checked} disabled> {text}</li>')
        elif stripped.startswith("- ") or stripped.startswith("* "):
            flush_para()
            text = inline(stripped[2:])
            if not in_ul or ul_is_checklist:
                close_ul()
                parts.append("<ul>")
                in_ul = True
            parts.append(f"<li>{text}</li>")
        elif stripped == "":
            close_ul(); flush_para()
        else:
            close_ul()
            para_lines.append(inline(stripped))

    # Đóng block còn mở cuối file
    if in_code_block:
        flush_code_block()
    close_ul()
    flush_para()

    body = "\n".join(parts)

    if qa_history:
        qa_parts = ['<div class="qa-section"><h2>Hỏi &amp; Đáp</h2>']
        for q, a in qa_history:
            qa_parts.append(f'<div class="qa-q">{html_lib.escape(q)}</div>')
            qa_parts.append(f'<div class="qa-a">{html_lib.escape(a)}</div>')
        qa_parts.append("</div>")
        body += "\n" + "\n".join(qa_parts)

    return _HTML_TEMPLATE.format(body=body)


class SummaryWorker(QThread):
    """Worker chạy trên thread riêng để tổng hợp tài liệu không block UI.

    Pipeline:
    1. Chuẩn bị nội dung từ extract cache (text, bảng, shapes, hình ảnh).
    2. Chunking nếu nội dung vượt context window (pre-summarize từng chunk).
    3. Gọi AI tạo báo cáo chi tiết, streaming toàn bộ lên UI.
    4. Lưu báo cáo .md vào thư mục tạm.

    Signals:
        status_updated: Phát khi cập nhật trạng thái (str thông báo).
        streaming_text: Phát text streaming cho UI typing effect (str chunk).
        detail_file_ready: Phát đường dẫn file .md (str path).
        cost_updated: Phát token usage (int input_tokens, int output_tokens).
        completed: Phát khi hoàn tất (bool thành_công, str lỗi).
    """

    status_updated = Signal(str)
    report_ready = Signal(str)
    detail_file_ready = Signal(str)
    cost_updated = Signal(int, int)
    completed = Signal(bool, str)

    def __init__(
        self,
        contents: dict[Path, ExtractedContent],
        provider: BaseProvider,
        parent: object = None,
    ) -> None:
        """Khởi tạo SummaryWorker.

        Args:
            contents: Dict {file_path: ExtractedContent} từ extract cache.
            provider: BaseProvider instance cho AI summarization.
            parent: QObject cha.
        """
        super().__init__(parent)
        self._contents = contents
        self._provider = provider
        self._cancelled = False
        config = ConfigManager()
        self._chunk_size: int = config.get("chunking.chunk_size", 100000)
        self._overlap_size: int = config.get("chunking.overlap_size", 500)

    def run(self) -> None:
        """Thực thi pipeline tổng hợp trên worker thread."""
        try:
            # Bước 1: Chuẩn bị nội dung từ tất cả file
            self.status_updated.emit("Analysing...")
            all_content = self._prepare_content()

            if self._cancelled:
                self.completed.emit(False, "Đã hủy")
                return

            # Bước 2: Chunking nếu nội dung quá lớn
            total_tokens = estimate_tokens(all_content)
            if total_tokens > self._chunk_size:
                self.status_updated.emit("Blending...")
                all_content = self._chunk_and_summarize(all_content)

            if self._cancelled:
                self.completed.emit(False, "Đã hủy")
                return

            # Bước 3: Tạo báo cáo chi tiết, streaming toàn bộ lên UI
            self.status_updated.emit("Summarizing...")
            detailed_report = self._generate_detailed_report(all_content)

            if self._cancelled:
                self.completed.emit(False, "Đã hủy")
                return

            # Bước 4: Lưu file .md
            md_path = self._save_report(detailed_report)
            self.detail_file_ready.emit(str(md_path))

            self.completed.emit(True, "")

        except Exception as e:
            logger.error("Summary worker lỗi: %s", e, exc_info=True)
            self.completed.emit(False, str(e))

    def cancel(self) -> None:
        """Yêu cầu hủy tổng hợp. Worker dừng sau bước đang xử lý."""
        self._cancelled = True
        logger.info("Đã yêu cầu hủy tổng hợp.")

    @property
    def is_cancelled(self) -> bool:
        """Kiểm tra worker đã bị hủy chưa."""
        return self._cancelled

    # --- Chuẩn bị nội dung ---

    def _prepare_content(self) -> str:
        """Chuẩn bị toàn bộ nội dung từ các file đã extract.

        Returns:
            Chuỗi text tổng hợp từ tất cả file.
        """
        parts: list[str] = []
        for content in self._contents.values():
            if self._cancelled:
                break
            parts.append(self._format_file_content(content))
        return "\n\n".join(parts)

    def _format_file_content(self, content: ExtractedContent) -> str:
        """Format nội dung một file thành text có cấu trúc.

        Args:
            content: ExtractedContent của file.

        Returns:
            Chuỗi text đã format.
        """
        size_str = self._format_size(content.file_size)
        parts = [f"=== File: {content.file_name} ({size_str}) ==="]

        # Text content
        full_text = content.get_full_text()
        if full_text:
            parts.append(full_text)

        # Bảng biểu
        for section, tables in content.tables.items():
            for table in tables:
                table_text = self._format_table(table)
                if table_text:
                    parts.append(f"[Bảng - {section}]\n{table_text}")

        # Shapes
        for section, texts in content.shapes_text.items():
            if texts:
                shapes_text = "\n".join(texts)
                parts.append(f"[Shapes - {section}]\n{shapes_text}")

        # Hình ảnh: mô tả bằng AI vision
        if content.images and not self._cancelled:
            for loc, img_data in content.images.items():
                desc = self._describe_image(img_data)
                if desc:
                    parts.append(f"[Hình ảnh - {loc}]\n{desc}")

        return "\n\n".join(parts)

    def _describe_image(self, image_data: bytes) -> str:
        """Mô tả hình ảnh bằng AI vision.

        Args:
            image_data: Dữ liệu ảnh dạng bytes.

        Returns:
            Mô tả text của hình ảnh.
        """
        try:
            text_parts: list[str] = []
            for chunk in self._provider.describe_image(image_data):
                if self._cancelled:
                    break
                if chunk.text:
                    text_parts.append(chunk.text)
                if chunk.is_final:
                    self.cost_updated.emit(chunk.input_tokens, chunk.output_tokens)
            return "".join(text_parts)
        except Exception as e:
            logger.warning("Không thể mô tả hình ảnh: %s", e)
            return "[Không thể mô tả hình ảnh]"

    # --- Chunking ---

    def _chunk_and_summarize(self, content: str) -> str:
        """Chia nội dung thành chunk và tổng hợp đệ quy.

        Khi nội dung vượt context window:
        1. Chia thành chunks (ưu tiên ranh giới file, có overlap).
        2. Tổng hợp từng chunk (có retry).
        3. Nếu tổng hợp vẫn quá lớn → đệ quy.

        Args:
            content: Nội dung cần chunking.

        Returns:
            Nội dung đã tổng hợp, vừa context window.
        """
        chunks = self._split_into_chunks(content)
        logger.info("Chia thành %d chunks để tổng hợp.", len(chunks))

        chunk_prompt = (
            "Bạn là trợ lý AI. Hãy tóm tắt nội dung sau một cách chi tiết, "
            "giữ lại tất cả thông tin quan trọng, số liệu, và tên file. "
            "Trả lời bằng tiếng Việt."
        )

        summaries: list[str] = []
        for i, chunk in enumerate(chunks):
            if self._cancelled:
                break
            self.status_updated.emit(f"Blending chunk {i + 1}/{len(chunks)}...")
            summary = self._call_summarize(chunk, chunk_prompt)
            if summary:
                summaries.append(summary)

        merged = "\n\n---\n\n".join(summaries)

        # Đệ quy nếu kết quả vẫn quá lớn
        if estimate_tokens(merged) > self._chunk_size and not self._cancelled:
            logger.info("Kết quả merge vẫn quá lớn, đệ quy chunking.")
            return self._chunk_and_summarize(merged)

        return merged

    def _split_into_chunks(self, content: str) -> list[str]:
        """Chia content thành chunks, ưu tiên ranh giới file.

        Args:
            content: Nội dung cần chia.

        Returns:
            Danh sách chunks.
        """
        file_parts = content.split("\n=== File: ")
        if len(file_parts) > 1:
            file_parts = [file_parts[0]] + [
                f"=== File: {p}" for p in file_parts[1:]
            ]
            return self._group_parts_into_chunks(file_parts)

        return self._split_by_tokens(content)

    def _group_parts_into_chunks(self, parts: list[str]) -> list[str]:
        """Gom các phần vào chunks sao cho không vượt chunk_size.

        Args:
            parts: Các đoạn nội dung (theo file).

        Returns:
            Danh sách chunks.
        """
        chunks: list[str] = []
        current = ""

        for part in parts:
            combined = f"{current}\n\n{part}" if current else part
            if estimate_tokens(combined) > self._chunk_size:
                if current:
                    chunks.append(current)
                if estimate_tokens(part) > self._chunk_size:
                    chunks.extend(self._split_by_tokens(part))
                else:
                    current = part
            else:
                current = combined

        if current:
            chunks.append(current)

        return chunks if chunks else ["\n\n".join(parts)]

    def _split_by_tokens(self, text: str) -> list[str]:
        """Chia text thành chunks theo số token, có overlap.

        Args:
            text: Nội dung cần chia.

        Returns:
            Danh sách chunks.
        """
        total_tokens = estimate_tokens(text)
        if total_tokens == 0:
            return [text]

        chars_per_token = len(text) / total_tokens
        chunk_chars = int(self._chunk_size * chars_per_token)
        overlap_chars = int(self._overlap_size * chars_per_token)

        chunks: list[str] = []
        start = 0

        while start < len(text):
            end = min(start + chunk_chars, len(text))

            if end < len(text):
                para_break = text.rfind("\n\n", start + chunk_chars // 2, end)
                if para_break > start:
                    end = para_break

            chunks.append(text[start:end])
            start = end - overlap_chars
            if start <= 0 and chunks:
                break

        return chunks if chunks else [text]

    # --- Gọi AI ---

    def _call_summarize(self, content: str, system_prompt: str) -> str:
        """Gọi AI summarize với retry khi gặp lỗi tạm thời.

        Dùng cho chunking pre-summarize (không stream lên UI).

        Args:
            content: Nội dung cần tổng hợp.
            system_prompt: System prompt tùy chỉnh.

        Returns:
            Nội dung đã tổng hợp.
        """
        for attempt in range(_MAX_RETRIES):
            try:
                text_parts: list[str] = []
                for chunk in self._provider.summarize(content, system_prompt):
                    if self._cancelled:
                        break
                    if chunk.text:
                        text_parts.append(chunk.text)
                    if chunk.is_final:
                        self.cost_updated.emit(chunk.input_tokens, chunk.output_tokens)
                return "".join(text_parts)
            except Exception as e:
                is_last = attempt == _MAX_RETRIES - 1
                if not _is_retryable(e) or is_last:
                    raise
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Summary API lỗi tạm thời (lần %d/%d), thử lại sau %.0fs: %s",
                    attempt + 1, _MAX_RETRIES, delay, e,
                )
                time.sleep(delay)
        return ""  # không đến được đây

    def _generate_detailed_report(self, content: str) -> str:
        """Tạo báo cáo chi tiết, streaming toàn bộ lên UI.

        Thay thế cả short summary lẫn detailed report cũ —
        một lần gọi AI, báo cáo hình thành trực tiếp trên màn hình.

        Args:
            content: Nội dung đã chuẩn bị (có thể đã qua chunking).

        Returns:
            Báo cáo Markdown đầy đủ.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        file_count = len(self._contents)
        provider_info = f"{self._provider.name} ({self._provider.model})"

        system_prompt = (
            "Bạn là trợ lý AI chuyên phân tích chuyên sâu và tổng hợp thông tin từ tài liệu.\n"
            "MỤC TIÊU: Giúp người đọc HIỂU RÕ nội dung mà KHÔNG cần đọc file gốc, "
            "KHÔNG cần tự tìm kiếm thêm thông tin.\n"
            "Nếu tài liệu mô tả mơ hồ, thiếu rõ ràng → bạn phải BỔ SUNG kiến thức để làm rõ.\n"
            "Nếu tài liệu giao việc → tổng hợp rõ ràng việc cần làm.\n\n"
            "Hãy tạo báo cáo theo CHÍNH XÁC cấu trúc Markdown sau:\n\n"
            "# Báo cáo tổng hợp tài liệu\n\n"
            f"- **Ngày tạo**: {now}\n"
            f"- **Số file xử lý**: {file_count} file\n"
            f"- **AI Provider**: {provider_info}\n\n"
            "---\n\n"
            "## 1. Tổng quan chung\n\n"
            "[Mô tả tổng quan ý nghĩa, mục đích chung (3-5 câu). "
            "Nêu mối liên hệ giữa các file hoặc ghi rõ nếu không liên quan.]\n\n"
            "---\n\n"
            "## 2. Phân tích từng file\n\n"
            "### 2.N. [Tên file gốc]\n"
            "- **Kích thước**: ...\n"
            "- **Loại tài liệu**: ...\n"
            "- **Ý nghĩa**: [File này phục vụ mục đích gì, nói về cái gì]\n"
            "- **Nội dung chính**:\n"
            "  - ...\n"
            "- **Bổ sung kiến thức**: [Nếu file đề cập thuật ngữ, khái niệm, "
            "quy trình nào mà có thể chưa rõ ràng → giải thích ngắn gọn. "
            "Bỏ qua mục này nếu nội dung đã rõ ràng.]\n"
            "- **Lưu ý đặc biệt**: ... (nếu có)\n\n"
            "(Lặp lại cho từng file)\n\n"
            "---\n\n"
            "## 3. Tổng hợp nội dung chi tiết\n\n"
            "[Tổng hợp chi tiết, kết nối thông tin giữa các file. "
            "Giải thích những phần mơ hồ dựa trên kiến thức của bạn. "
            "Nếu các file giao việc/yêu cầu hành động → liệt kê rõ ràng. "
            "Tự điều chỉnh các heading phù hợp nội dung thực tế.]\n\n"
            "---\n\n"
            "## 4. Đề xuất và hướng đi tiếp theo\n\n"
            "[Dựa trên nội dung phân tích, đưa ra:\n"
            "- Việc cần làm cụ thể (nếu tài liệu giao việc)\n"
            "- Giải pháp/hướng tiếp cận (nếu tài liệu nêu vấn đề)\n"
            "- Câu hỏi cần làm rõ với người gửi tài liệu "
            "(nếu có điểm mơ hồ, thiếu thông tin, hoặc mâu thuẫn)\n"
            "- Tài liệu/kiến thức nên tìm hiểu thêm (nếu cần)]\n\n"
            "- [ ] ...\n\n"
            "Quy tắc:\n"
            "- Viết hoàn toàn bằng tiếng Việt\n"
            "- Sử dụng checkbox markdown cho phần đề xuất\n"
            "- QUAN TRỌNG: Đừng chỉ tóm tắt — hãy PHÂN TÍCH, BỔ SUNG, và ĐỀ XUẤT. "
            "Mục tiêu là người đọc hiểu mọi thứ từ báo cáo này mà không cần "
            "tra Google hay hỏi thêm ai.\n\n"
            "TRỰC QUAN HÓA VỚI MERMAID:\n"
            "Báo cáo sẽ được render thành HTML — bạn có thể dùng Mermaid diagram "
            "bằng cách dùng code block ```mermaid. Các trường hợp điển hình:\n"
            "- Timeline, lịch trình, deadline → gantt\n"
            "- Quy trình, luồng xử lý, kiến trúc hệ thống → flowchart\n"
            "- Phân bổ tỉ lệ, thống kê → pie\n"
            "- So sánh số liệu nhiều chiều → xychart-beta\n"
            "- Quan hệ giữa các thực thể → erDiagram\n"
            "Ngoài các trường hợp trên, hãy TỰ ĐÁNH GIÁ toàn bộ nội dung: "
            "bất kỳ phần nào mà một sơ đồ hoặc biểu đồ giúp người đọc hiểu "
            "nhanh hơn văn bản mô tả — hãy ưu tiên thêm Mermaid thay vì text. "
            "Không ép buộc diagram nếu nội dung không phù hợp."
        )

        text_parts: list[str] = []
        for chunk in self._provider.summarize(content, system_prompt):
            if self._cancelled:
                break
            if chunk.text:
                text_parts.append(chunk.text)
            if chunk.is_final:
                self.cost_updated.emit(chunk.input_tokens, chunk.output_tokens)

        full_report = "".join(text_parts)
        if full_report:
            self.report_ready.emit(full_report)
        return full_report

    # --- Lưu kết quả ---

    def _save_report(self, report: str) -> Path:
        """Lưu báo cáo chi tiết dạng HTML vào file tạm (chưa download).

        File sẽ được copy sang Downloads khi người dùng bấm "Chi tiết".

        Args:
            report: Nội dung báo cáo Markdown.

        Returns:
            Đường dẫn file HTML tạm đã lưu.
        """
        import tempfile

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"lazydoc_summary_{timestamp}.html"
        tmp_dir = Path(tempfile.gettempdir()) / "lazydoc"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / filename

        html_content = _md_to_html(report)
        tmp_path.write_text(html_content, encoding="utf-8")
        logger.info("Đã lưu báo cáo tạm: %s", tmp_path)
        return tmp_path

    # --- Utilities ---

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format kích thước file sang đơn vị dễ đọc."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes / (1024 * 1024):.1f} MB"

    @staticmethod
    def _format_table(table: list[list[str]]) -> str:
        """Format bảng thành text dạng pipe-separated.

        Args:
            table: Dữ liệu bảng [[row1], [row2], ...].

        Returns:
            Chuỗi text đã format.
        """
        if not table:
            return ""
        lines: list[str] = []
        for row in table:
            lines.append(" | ".join(str(cell) for cell in row))
        return "\n".join(lines)
