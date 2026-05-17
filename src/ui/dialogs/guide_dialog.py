"""GuideDialog — Hướng dẫn sử dụng LazyDoc."""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.ui import theme


# Màu sắc áp dụng trong HTML content (inline style)
_H2 = theme.MAUVE
_H3 = theme.BLUE
_BODY = theme.SUBTEXT_1
_ACCENT = theme.GREEN
_MUTED = theme.SUBTEXT_0
_LINK = theme.SAPPHIRE


def _tab_html(content: str) -> str:
    return f"""
    <html><body style="
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
        color: {_BODY};
        background: transparent;
        line-height: 1.65;
        padding: 4px 8px;
    ">
    {content}
    </body></html>
    """


_HTML_START = _tab_html(f"""
<h2 style="color:{_H2}; margin-bottom:4px;">Bắt đầu</h2>
<p>LazyDoc giúp bạn tổng hợp và dịch thuật tài liệu nhanh chóng bằng AI.</p>

<h3 style="color:{_H3}; margin-top:16px; margin-bottom:4px;">1. Tạo API Key</h3>
<p>Chọn một trong các nhà cung cấp AI sau và tạo API key miễn phí:</p>
<ul style="margin-top:4px; padding-left:20px;">
  <li style="margin-bottom:6px;">
    <b>Google Gemini</b> — Miễn phí, quota hào phóng<br>
    <a style="color:{_LINK};" href="https://aistudio.google.com/apikey">
      https://aistudio.google.com/apikey
    </a>
  </li>
  <li style="margin-bottom:6px;">
    <b>OpenAI GPT</b> — Chất lượng cao, cần nạp credit<br>
    <a style="color:{_LINK};" href="https://platform.openai.com/api-keys">
      https://platform.openai.com/api-keys
    </a>
  </li>
  <li style="margin-bottom:6px;">
    <b>Anthropic Claude</b> — Mạnh về phân tích văn bản<br>
    <a style="color:{_LINK};" href="https://console.anthropic.com/">
      https://console.anthropic.com/
    </a>
  </li>
</ul>

<h3 style="color:{_H3}; margin-top:16px; margin-bottom:4px;">2. Nhập API Key vào ứng dụng</h3>
<p>Click nút <b>⚙ Cài đặt</b> trên thanh công cụ → chọn provider → dán API key → Lưu.<br>
Ứng dụng sẽ tự kiểm tra key có hợp lệ không trước khi lưu.</p>

<h3 style="color:{_H3}; margin-top:16px; margin-bottom:4px;">3. Thêm file</h3>
<p>Kéo thả file vào vùng trung tâm, hoặc click vào vùng đó để mở hộp thoại chọn file.<br>
Tick chọn các file muốn xử lý trong bảng danh sách bên phải.</p>

<p style="color:{_MUTED}; margin-top:16px; font-size:12px;">
  Định dạng hỗ trợ: DOCX, XLSX, PPTX, TXT, MD, CSV, PNG, JPG, BMP, GIF
</p>
""")

_HTML_SUMMARY = _tab_html(f"""
<h2 style="color:{_H2}; margin-bottom:4px;">Tổng hợp tài liệu</h2>
<p>Click nút <b>Tổng hợp</b> để AI phân tích và trích xuất thông tin quan trọng từ file.</p>

<h3 style="color:{_H3}; margin-top:16px; margin-bottom:4px;">Quy trình</h3>
<ol style="padding-left:20px; margin-top:4px;">
  <li style="margin-bottom:6px;">Tick chọn file cần tổng hợp</li>
  <li style="margin-bottom:6px;">Click <b>Tổng hợp</b> — ứng dụng tự động đọc file và gửi lên AI</li>
  <li style="margin-bottom:6px;">Đọc tổng quan ngay trên màn hình chính</li>
  <li style="margin-bottom:6px;">Click <b>Chi tiết ↓</b> để tải báo cáo đầy đủ định dạng HTML</li>
</ol>

<h3 style="color:{_H3}; margin-top:16px; margin-bottom:4px;">Hỏi đáp (Q&amp;A)</h3>
<p>Sau khi tổng hợp xong, một ô nhập xuất hiện bên dưới — bạn có thể đặt bất kỳ
câu hỏi nào về nội dung tài liệu.</p>
<ul style="padding-left:20px; margin-top:4px;">
  <li style="margin-bottom:4px;">AI trả lời dựa trên <b>toàn bộ nội dung</b> đã tổng hợp</li>
  <li style="margin-bottom:4px;">Hỗ trợ nhiều lượt hỏi liên tiếp — AI nhớ ngữ cảnh hội thoại</li>
  <li style="margin-bottom:4px;">Khi tải báo cáo Chi tiết, toàn bộ Q&amp;A sẽ được đính kèm vào file HTML</li>
</ul>

<h3 style="color:{_H3}; margin-top:16px; margin-bottom:4px;">Lưu ý</h3>
<ul style="padding-left:20px; margin-top:4px;">
  <li style="margin-bottom:4px;">Cần cấu hình AI Provider trước khi sử dụng tính năng này</li>
  <li style="margin-bottom:4px;">File hình ảnh (PNG, JPG…) được phân tích bằng AI vision — cần provider hỗ trợ</li>
  <li style="margin-bottom:4px;">Có thể tổng hợp nhiều file cùng lúc — AI sẽ so sánh và liên kết thông tin</li>
</ul>
""")

_HTML_TRANSLATE = _tab_html(f"""
<h2 style="color:{_H2}; margin-bottom:4px;">Dịch thuật</h2>
<p>Click nút <b>Dịch</b> để mở hộp thoại dịch thuật. File đầu ra được lưu vào
thư mục <b>Downloads</b>, giữ nguyên định dạng gốc.</p>

<h3 style="color:{_H3}; margin-top:16px; margin-bottom:4px;">Hai chế độ dịch</h3>
<table style="width:100%; border-collapse:collapse; margin-top:4px;">
  <tr>
    <td style="padding:8px 12px; background:{theme.SURFACE_0};
               border-radius:6px; width:50%; vertical-align:top;">
      <b style="color:{_ACCENT};">Nhanh (Offline)</b><br>
      <span style="font-size:12px; color:{_MUTED};">
        Dùng Argos Translate<br>
        • Không cần internet<br>
        • Hoàn toàn miễn phí<br>
        • Tốc độ nhanh<br>
        • Phù hợp văn bản thông thường
      </span>
    </td>
    <td style="width:8px;"></td>
    <td style="padding:8px 12px; background:{theme.SURFACE_0};
               border-radius:6px; vertical-align:top;">
      <b style="color:{theme.MAUVE};">Thông minh (AI)</b><br>
      <span style="font-size:12px; color:{_MUTED};">
        Dùng AI Provider đã cấu hình<br>
        • Chất lượng cao<br>
        • Hiểu ngữ cảnh và thuật ngữ<br>
        • Hỗ trợ lĩnh vực chuyên ngành<br>
        • Cần API key và quota
      </span>
    </td>
  </tr>
</table>

<h3 style="color:{_H3}; margin-top:16px; margin-bottom:4px;">Ngữ cảnh dịch (Smart mode)</h3>
<p>Nếu bạn đã <b>Tổng hợp</b> tài liệu trước, nội dung tổng hợp sẽ tự động được
gửi kèm như ngữ cảnh cho AI khi dịch — giúp AI hiểu đúng domain và dịch
thuật ngữ chuyên ngành nhất quán hơn.</p>

<h3 style="color:{_H3}; margin-top:16px; margin-bottom:4px;">Bảng thuật ngữ (Glossary)</h3>
<p>Click <b>Bảng thuật ngữ</b> trong hộp thoại dịch để quản lý thuật ngữ tùy chỉnh.</p>
<ul style="padding-left:20px; margin-top:4px;">
  <li style="margin-bottom:4px;">Thêm cặp thuật ngữ nguồn → đích theo từng ngôn ngữ</li>
  <li style="margin-bottom:4px;"><b>Import CSV</b>: nạp bảng thuật ngữ từ file có sẵn</li>
  <li style="margin-bottom:4px;"><b>Export CSV</b>: xuất ra để chia sẻ hoặc backup</li>
  <li style="margin-bottom:4px;">Thuật ngữ được ưu tiên áp dụng khi dịch — đảm bảo nhất quán</li>
</ul>

<h3 style="color:{_H3}; margin-top:16px; margin-bottom:4px;">Tùy chọn thêm (Smart mode)</h3>
<ul style="padding-left:20px; margin-top:4px;">
  <li style="margin-bottom:4px;"><b>Lĩnh vực</b>: IT, Y tế, Pháp lý, Tài chính… → AI dùng văn phong đúng ngành</li>
  <li style="margin-bottom:4px;"><b>Văn phong</b>: Báo cáo, Ngắn gọn, Văn học… → điều chỉnh tone dịch</li>
</ul>
""")


class GuideDialog(QDialog):
    """Dialog hướng dẫn sử dụng."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_window()
        self._setup_ui()
        self._setup_style()

    def _setup_window(self) -> None:
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.setMinimumSize(580, 500)
        self.resize(600, 540)

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        panel = QWidget()
        panel.setObjectName("guidePanel")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 130))
        panel.setGraphicsEffect(shadow)
        outer.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 20)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("guideHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 12, 14)

        from PySide6.QtWidgets import QLabel
        title = QLabel("Hướng dẫn sử dụng")
        title.setObjectName("guideTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        close_btn = QPushButton()
        close_btn.setObjectName("guideCloseBtn")
        close_btn.setIcon(theme.icon("close", theme.SUBTEXT_0))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        header_layout.addWidget(close_btn)
        layout.addWidget(header)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setObjectName("guideTabs")
        self._tabs.addTab(self._make_tab(_HTML_START), "Bắt đầu")
        self._tabs.addTab(self._make_tab(_HTML_SUMMARY), "Tổng hợp")
        self._tabs.addTab(self._make_tab(_HTML_TRANSLATE), "Dịch thuật")
        layout.addWidget(self._tabs)

    def _make_tab(self, html: str) -> QWidget:
        browser = QTextBrowser()
        browser.setObjectName("guideBrowser")
        browser.setOpenLinks(False)
        browser.setHtml(html)
        browser.anchorClicked.connect(
            lambda url: QDesktopServices.openUrl(url)
        )
        return browser

    def _setup_style(self) -> None:
        self.setStyleSheet(f"""
            GuideDialog {{
                background-color: {theme.BG_CRUST};
            }}
            #guidePanel {{
                background-color: {theme.BG_MANTLE};
                border: 1px solid {theme.SURFACE_1};
                border-radius: {theme.RADIUS_LG}px;
            }}
            #guideHeader {{
                background-color: {theme.SURFACE_0};
                border-top-left-radius: {theme.RADIUS_LG}px;
                border-top-right-radius: {theme.RADIUS_LG}px;
                border-bottom: 1px solid {theme.SURFACE_1};
            }}
            #guideTitle {{
                color: {theme.TEXT};
                font-size: {theme.FONT_MD}px;
                font-weight: bold;
                background: transparent;
            }}
            #guideCloseBtn {{
                background: transparent;
                border: none;
                border-radius: {theme.RADIUS_SM}px;
            }}
            #guideCloseBtn:hover {{ background-color: {theme.SURFACE_1}; }}
            #guideTabs {{
                background: transparent;
                border: none;
            }}
            #guideTabs::pane {{
                border: none;
                background: transparent;
            }}
            #guideTabs QTabBar::tab {{
                background: transparent;
                color: {theme.SUBTEXT_0};
                padding: 8px 20px;
                font-size: {theme.FONT_SM}px;
                border: none;
                border-bottom: 2px solid transparent;
                margin-right: 2px;
            }}
            #guideTabs QTabBar::tab:selected {{
                color: {theme.MAUVE};
                border-bottom: 2px solid {theme.MAUVE};
                font-weight: bold;
            }}
            #guideTabs QTabBar::tab:hover:!selected {{
                color: {theme.TEXT};
            }}
            #guideBrowser {{
                background-color: transparent;
                border: none;
                color: {theme.SUBTEXT_1};
                font-size: {theme.FONT_SM}px;
                padding: 8px 16px;
            }}
        """)
