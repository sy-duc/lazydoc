"""LazyDoc — Entry point của ứng dụng."""

import sys
import logging
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Trong PyInstaller bundle, sys._MEIPASS trỏ đến thư mục chứa bundled resources
if getattr(sys, "frozen", False):
    APP_ICON_PATH = Path(sys._MEIPASS) / "favicon.ico"
else:
    APP_ICON_PATH = PROJECT_ROOT / "favicon.ico"

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.core.logging_config import configure_logging
from src.core.database import DatabaseManager
from src.core.config import ConfigManager
from src.core.i18n import I18nManager
from src.providers.provider_manager import ProviderManager
from src.ui.main_window import MainWindow

configure_logging()
logger = logging.getLogger("lazydoc")


def main() -> None:
    """Khởi chạy ứng dụng LazyDoc."""
    logger.info("Đang khởi động LazyDoc...")

    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "LazyDoc.LazyDoc"
        )

    # Khởi tạo core services
    config = ConfigManager()
    logger.info("Config đã được load thành công.")

    db = DatabaseManager()
    db.initialize()
    logger.info("Database đã được khởi tạo.")

    i18n = I18nManager()
    logger.info("I18n đã được khởi tạo (ngôn ngữ: %s).", i18n.current_language)

    # Khởi tạo AI Provider Manager
    provider_manager = ProviderManager()
    loaded = provider_manager.load_active_provider()
    if loaded:
        logger.info("AI Provider đã sẵn sàng: %s", provider_manager.provider_name)
    else:
        logger.info("AI Provider chưa có API key. Vui lòng cấu hình trong Settings.")

    # Khởi chạy giao diện
    app = QApplication(sys.argv)
    icon = QIcon(str(APP_ICON_PATH))
    app.setWindowIcon(icon)
    window = MainWindow(provider_manager=provider_manager)
    window.setWindowIcon(icon)
    window.show()
    logger.info("LazyDoc khởi động hoàn tất.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
