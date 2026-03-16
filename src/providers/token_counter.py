"""TokenCounter — Đếm token và tính chi phí API."""

import logging
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal

from src.core.config import ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class UsageStats:
    """Thống kê sử dụng token và chi phí.

    Attributes:
        input_tokens: Tổng token đầu vào.
        output_tokens: Tổng token đầu ra.
        total_tokens: Tổng token (input + output).
        input_cost: Chi phí token đầu vào (USD).
        output_cost: Chi phí token đầu ra (USD).
        total_cost: Tổng chi phí (USD).
    """

    input_tokens: int = 0
    output_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def total_cost(self) -> float:
        return self.input_cost + self.output_cost


def estimate_tokens(text: str) -> int:
    """Ước tính số token từ text (phương pháp đơn giản).

    Sử dụng heuristic: ~4 ký tự = 1 token cho tiếng Anh,
    ~2 ký tự = 1 token cho tiếng Việt/CJK.

    Args:
        text: Chuỗi cần ước tính.

    Returns:
        Số token ước tính.
    """
    if not text:
        return 0

    # Đếm ký tự non-ASCII (tiếng Việt, CJK, ...)
    non_ascii = sum(1 for c in text if ord(c) > 127)
    ascii_chars = len(text) - non_ascii

    # Ước tính: ASCII ~4 chars/token, non-ASCII ~2 chars/token
    return int(ascii_chars / 4 + non_ascii / 2)


class TokenCounter(QObject):
    """Đếm token và tính chi phí realtime.

    Tích lũy usage qua nhiều lần gọi API trong một phiên,
    emit signal để UI cập nhật.

    Signals:
        usage_updated: Phát khi có cập nhật usage (int total_tokens, float total_cost).
    """

    usage_updated = Signal(int, float)

    def __init__(self, parent: QObject | None = None) -> None:
        """Khởi tạo TokenCounter."""
        super().__init__(parent)
        self._config = ConfigManager()
        self._stats = UsageStats()

    @property
    def stats(self) -> UsageStats:
        """Trả về thống kê hiện tại."""
        return self._stats

    def add_usage(
        self,
        provider_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Cộng dồn usage từ một lần gọi API.

        Args:
            provider_name: Tên provider (gemini, openai, claude).
            model: Tên model đã sử dụng.
            input_tokens: Số token đầu vào.
            output_tokens: Số token đầu ra.
        """
        # Lấy giá từ config (USD per 1M tokens)
        input_price = self._config.get(f"pricing.{provider_name}.{model}.input", 0)
        output_price = self._config.get(f"pricing.{provider_name}.{model}.output", 0)

        # Tính chi phí
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price

        # Cộng dồn
        self._stats.input_tokens += input_tokens
        self._stats.output_tokens += output_tokens
        self._stats.input_cost += input_cost
        self._stats.output_cost += output_cost

        logger.debug(
            "Token usage: +%d in, +%d out | Tổng: %d tokens, $%.4f",
            input_tokens,
            output_tokens,
            self._stats.total_tokens,
            self._stats.total_cost,
        )

        # Emit signal cập nhật UI
        self.usage_updated.emit(
            self._stats.total_tokens,
            self._stats.total_cost,
        )

    def reset(self) -> None:
        """Reset thống kê về 0 (bắt đầu phiên mới)."""
        self._stats = UsageStats()
        self.usage_updated.emit(0, 0.0)
        logger.info("Đã reset token counter.")
