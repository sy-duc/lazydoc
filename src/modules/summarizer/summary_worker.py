"""SummaryWorker — Worker thread cho quá trình tổng hợp tài liệu."""

import logging
import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.core.config import ConfigManager
from src.processors.base import ExtractedContent
from src.providers.base import BaseProvider
from src.providers.token_counter import estimate_tokens

logger = logging.getLogger(__name__)


class SummaryWorker(QThread):
    """Worker chạy trên thread riêng để tổng hợp tài liệu không block UI.

    Pipeline:
    1. Chuẩn bị nội dung từ extract cache (text, bảng, shapes, hình ảnh).
    2. Chunking nếu nội dung vượt context window.
    3. Gọi AI tạo tóm tắt ngắn (streaming lên UI).
    4. Gọi AI tạo báo cáo chi tiết theo template.
    5. Parse thông tin từng file (ý nghĩa, ngôn ngữ) → cập nhật bảng.
    6. Lưu báo cáo .md vào Downloads.

    Signals:
        status_updated: Phát khi cập nhật trạng thái (str thông báo).
        streaming_text: Phát text streaming cho UI typing effect (str chunk).
        file_info_ready: Phát thông tin từng file (str tên_file, str ý_nghĩa, str ngôn_ngữ).
        detail_file_ready: Phát đường dẫn file .md (str path).
        cost_updated: Phát token usage (int input_tokens, int output_tokens).
        completed: Phát khi hoàn tất (bool thành_công, str lỗi).
    """

    status_updated = Signal(str)
    streaming_text = Signal(str)
    file_info_ready = Signal(str, str, str)
    detail_file_ready = Signal(str)
    cost_updated = Signal(int, int)
    completed = Signal(bool, str)

    def __init__(
        self,
        contents: dict[Path, ExtractedContent],
        provider: BaseProvider,
        output_dir: Path,
        parent: object = None,
    ) -> None:
        """Khởi tạo SummaryWorker.

        Args:
            contents: Dict {file_path: ExtractedContent} từ extract cache.
            provider: BaseProvider instance cho AI summarization.
            output_dir: Thư mục lưu file .md (Downloads).
            parent: QObject cha.
        """
        super().__init__(parent)
        self._contents = contents
        self._provider = provider
        self._output_dir = output_dir
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

            # Bước 3: Tạo tóm tắt ngắn (streaming lên UI)
            self.status_updated.emit("Summarizing...")
            self._generate_short_summary(all_content)

            if self._cancelled:
                self.completed.emit(False, "Đã hủy")
                return

            # Bước 4: Tạo báo cáo chi tiết
            self.status_updated.emit("Generating report...")
            detailed_report = self._generate_detailed_report(all_content)

            if self._cancelled:
                self.completed.emit(False, "Đã hủy")
                return

            # Bước 5: Parse thông tin từng file từ báo cáo
            self._parse_file_info(detailed_report)

            # Bước 6: Lưu file .md
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
        2. Tổng hợp từng chunk.
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
        # Thử chia theo ranh giới file (=== File: ... ===)
        file_parts = content.split("\n=== File: ")
        if len(file_parts) > 1:
            # Khôi phục prefix cho các phần sau phần đầu
            file_parts = [file_parts[0]] + [
                f"=== File: {p}" for p in file_parts[1:]
            ]
            return self._group_parts_into_chunks(file_parts)

        # Không có ranh giới file → chia theo token
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
                # Nếu một file đơn lẻ quá lớn → chia tiếp
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

            # Cố gắng cắt tại ranh giới đoạn
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
        """Gọi AI summarize, thu thập toàn bộ response (không stream lên UI).

        Args:
            content: Nội dung cần tổng hợp.
            system_prompt: System prompt tùy chỉnh.

        Returns:
            Nội dung đã tổng hợp.
        """
        text_parts: list[str] = []
        for chunk in self._provider.summarize(content, system_prompt):
            if self._cancelled:
                break
            if chunk.text:
                text_parts.append(chunk.text)
            if chunk.is_final:
                self.cost_updated.emit(chunk.input_tokens, chunk.output_tokens)
        return "".join(text_parts)

    def _generate_short_summary(self, content: str) -> str:
        """Tạo tóm tắt ngắn, streaming text lên UI.

        Args:
            content: Nội dung đã chuẩn bị (có thể đã qua chunking).

        Returns:
            Bản tóm tắt ngắn.
        """
        file_count = len(self._contents)
        if file_count == 1:
            system_prompt = (
                "Bạn là trợ lý AI chuyên phân tích và tổng hợp thông tin từ tài liệu.\n"
                "Bạn nhận được nội dung của MỘT file duy nhất.\n\n"
                "Hãy viết tóm tắt ngắn gọn (3-5 câu) gồm:\n"
                "- File này nói về cái gì, phục vụ mục đích gì.\n"
                "- Thông điệp chính hoặc nội dung cốt lõi mà file muốn truyền tải.\n"
                "- Nếu nội dung còn mơ hồ hoặc thiếu rõ ràng, "
                "chỉ ra ngắn gọn điểm nào cần làm rõ.\n\n"
                "Trả lời bằng tiếng Việt."
            )
        else:
            system_prompt = (
                "Bạn là trợ lý AI chuyên phân tích và tổng hợp thông tin từ tài liệu.\n"
                f"Bạn nhận được nội dung của {file_count} file.\n\n"
                "Hãy viết tóm tắt ngắn gọn (3-7 câu):\n"
                "- Đầu tiên, xác định xem các file có LIÊN QUAN đến nhau không.\n"
                "- Nếu CÓ liên quan: tóm tắt thông điệp/mục đích chung mà toàn bộ "
                "các file muốn truyền tải khi kết hợp lại, "
                "và nêu ngắn gọn vai trò của từng file trong bức tranh tổng thể.\n"
                "- Nếu KHÔNG liên quan: nói rõ các file không liên quan đến nhau, "
                "sau đó tóm tắt ý nghĩa từng file (1 câu mỗi file).\n"
                "- Nếu nội dung còn mơ hồ hoặc thiếu rõ ràng, "
                "chỉ ra ngắn gọn điểm nào cần làm rõ.\n\n"
                "Trả lời bằng tiếng Việt."
            )

        text_parts: list[str] = []
        for chunk in self._provider.summarize(content, system_prompt):
            if self._cancelled:
                break
            if chunk.text:
                self.streaming_text.emit(chunk.text)
                text_parts.append(chunk.text)
            if chunk.is_final:
                self.cost_updated.emit(chunk.input_tokens, chunk.output_tokens)
        return "".join(text_parts)

    def _generate_detailed_report(self, content: str) -> str:
        """Tạo báo cáo chi tiết theo template.

        Args:
            content: Nội dung đã chuẩn bị.

        Returns:
            Báo cáo Markdown chi tiết.
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
            "[Mô tả tổng quan ý nghĩa, mục đích chung. "
            "Nêu mối liên hệ giữa các file hoặc ghi rõ nếu không liên quan.]\n\n"
            "---\n\n"
            "## 2. Phân tích từng file\n\n"
            "### 2.N. [Tên file gốc]\n"
            "- **Kích thước**: ...\n"
            "- **Ngôn ngữ**: ... (bỏ qua dòng này nếu file chỉ có tiếng Việt)\n"
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
            "- Xác định ngôn ngữ chính của từng file (chỉ ghi nếu không phải tiếng Việt)\n"
            "- Xác định ý nghĩa/mục đích cụ thể từng file\n"
            "- Sử dụng checkbox markdown cho phần đề xuất\n"
            "- QUAN TRỌNG: Đừng chỉ tóm tắt — hãy PHÂN TÍCH, BỔ SUNG, và ĐỀ XUẤT. "
            "Mục tiêu là người đọc hiểu mọi thứ từ báo cáo này mà không cần "
            "tra Google hay hỏi thêm ai."
        )

        return self._call_summarize(content, system_prompt)

    # --- Parse và lưu kết quả ---

    def _parse_file_info(self, report: str) -> None:
        """Parse thông tin từng file từ báo cáo chi tiết.

        Tìm các section ### 2.N. [tên file] và trích xuất:
        - Ý nghĩa (từ dòng **Ý nghĩa**)
        - Ngôn ngữ (từ dòng **Ngôn ngữ**, nếu có)

        Args:
            report: Báo cáo Markdown chi tiết.
        """
        # Tách các section file: ### 2.N. tên_file
        sections = re.split(r"### 2\.\d+\.\s+", report)

        for section in sections[1:]:  # Bỏ phần trước file đầu tiên
            lines = section.strip().split("\n")
            if not lines:
                continue

            file_name = lines[0].strip()
            purpose = ""
            language = ""

            for line in lines[1:]:
                stripped = line.strip()
                if stripped.startswith("- **Ý nghĩa**:"):
                    purpose = stripped.replace("- **Ý nghĩa**:", "").strip()
                elif stripped.startswith("- **Ngôn ngữ**:"):
                    language = stripped.replace("- **Ngôn ngữ**:", "").strip()

            if file_name:
                self.file_info_ready.emit(file_name, purpose, language)

    def _save_report(self, report: str) -> Path:
        """Lưu báo cáo chi tiết vào file .md trong thư mục Downloads.

        Args:
            report: Nội dung báo cáo Markdown.

        Returns:
            Đường dẫn file đã lưu.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"lazydoc_summary_{timestamp}.md"
        md_path = self._output_dir / filename

        self._output_dir.mkdir(parents=True, exist_ok=True)
        md_path.write_text(report, encoding="utf-8")
        logger.info("Đã lưu báo cáo tổng hợp: %s", md_path)
        return md_path

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
