"""LazyDoc — Entry point của ứng dụng."""

import sys
import logging
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

from src.core.database import DatabaseManager
from src.core.config import ConfigManager
from src.core.i18n import I18nManager
from src.ui.main_window import MainWindow

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("lazydoc")


def main() -> None:
    """Khởi chạy ứng dụng LazyDoc."""
    logger.info("Đang khởi động LazyDoc...")

    # Khởi tạo core services
    config = ConfigManager()
    logger.info("Config đã được load thành công.")

    db = DatabaseManager()
    db.initialize()
    logger.info("Database đã được khởi tạo.")

    i18n = I18nManager()
    logger.info("I18n đã được khởi tạo (ngôn ngữ: %s).", i18n.current_language)

    # Khởi chạy giao diện
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    logger.info("LazyDoc khởi động hoàn tất.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
