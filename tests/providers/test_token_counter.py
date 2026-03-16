"""Test TokenCounter — Kiểm tra đếm token và tính chi phí."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.providers.token_counter import TokenCounter, UsageStats, estimate_tokens


class TestUsageStats:
    """Test UsageStats dataclass."""

    def test_default_values(self) -> None:
        stats = UsageStats()
        assert stats.input_tokens == 0
        assert stats.output_tokens == 0
        assert stats.total_tokens == 0
        assert stats.input_cost == 0.0
        assert stats.output_cost == 0.0
        assert stats.total_cost == 0.0

    def test_total_tokens(self) -> None:
        stats = UsageStats(input_tokens=100, output_tokens=50)
        assert stats.total_tokens == 150

    def test_total_cost(self) -> None:
        stats = UsageStats(input_cost=0.001, output_cost=0.003)
        assert stats.total_cost == pytest.approx(0.004)


class TestEstimateTokens:
    """Test hàm estimate_tokens."""

    def test_empty_string(self) -> None:
        assert estimate_tokens("") == 0

    def test_ascii_text(self) -> None:
        # "Hello world" = 11 ký tự ASCII → ~2.75 → 2 tokens
        result = estimate_tokens("Hello world")
        assert result > 0
        assert result < 10

    def test_vietnamese_text(self) -> None:
        # Tiếng Việt có nhiều non-ASCII → nhiều token hơn per character
        result = estimate_tokens("Xin chào thế giới")
        assert result > 0

    def test_mixed_text(self) -> None:
        result = estimate_tokens("Hello thế giới 123")
        assert result > 0


class TestTokenCounter:
    """Test TokenCounter class."""

    @pytest.fixture
    def mock_config(self):
        """Mock ConfigManager để không đọc file config thật."""
        with patch("src.providers.token_counter.ConfigManager") as mock_cls:
            config_instance = MagicMock()
            # Trả về giá token test
            def get_pricing(key, default=None):
                prices = {
                    "pricing.gemini.gemini-1.5-flash.input": 0.075,
                    "pricing.gemini.gemini-1.5-flash.output": 0.30,
                    "pricing.openai.gpt-4o.input": 2.50,
                    "pricing.openai.gpt-4o.output": 10.00,
                    "pricing.claude.claude-haiku-4-5-20251001.input": 0.80,
                    "pricing.claude.claude-haiku-4-5-20251001.output": 4.00,
                }
                return prices.get(key, default)

            config_instance.get.side_effect = get_pricing
            mock_cls.return_value = config_instance
            yield config_instance

    @pytest.fixture
    def counter(self, mock_config):
        """Tạo TokenCounter instance."""
        return TokenCounter()

    def test_initial_stats(self, counter: TokenCounter) -> None:
        assert counter.stats.total_tokens == 0
        assert counter.stats.total_cost == 0.0

    def test_add_usage_gemini(self, counter: TokenCounter) -> None:
        counter.add_usage("gemini", "gemini-1.5-flash", 1000, 500)

        assert counter.stats.input_tokens == 1000
        assert counter.stats.output_tokens == 500
        assert counter.stats.total_tokens == 1500

        # Chi phí: input = 1000/1M * 0.075 = 0.000075
        #          output = 500/1M * 0.30 = 0.000150
        expected_cost = (1000 / 1_000_000) * 0.075 + (500 / 1_000_000) * 0.30
        assert counter.stats.total_cost == pytest.approx(expected_cost)

    def test_add_usage_accumulates(self, counter: TokenCounter) -> None:
        counter.add_usage("gemini", "gemini-1.5-flash", 1000, 500)
        counter.add_usage("gemini", "gemini-1.5-flash", 2000, 1000)

        assert counter.stats.input_tokens == 3000
        assert counter.stats.output_tokens == 1500

    def test_add_usage_openai(self, counter: TokenCounter) -> None:
        counter.add_usage("openai", "gpt-4o", 1000, 500)

        expected_cost = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
        assert counter.stats.total_cost == pytest.approx(expected_cost)

    def test_reset(self, counter: TokenCounter) -> None:
        counter.add_usage("gemini", "gemini-1.5-flash", 1000, 500)
        counter.reset()

        assert counter.stats.total_tokens == 0
        assert counter.stats.total_cost == 0.0

    def test_signal_emitted(self, counter: TokenCounter) -> None:
        """Kiểm tra signal usage_updated được emit."""
        signal_received = []
        counter.usage_updated.connect(
            lambda tokens, cost: signal_received.append((tokens, cost))
        )

        counter.add_usage("gemini", "gemini-1.5-flash", 1000, 500)

        assert len(signal_received) == 1
        assert signal_received[0][0] == 1500  # total tokens

    def test_reset_emits_signal(self, counter: TokenCounter) -> None:
        """Kiểm tra reset emit signal với giá trị 0."""
        signal_received = []
        counter.usage_updated.connect(
            lambda tokens, cost: signal_received.append((tokens, cost))
        )

        counter.reset()

        assert len(signal_received) == 1
        assert signal_received[0] == (0, 0.0)

    def test_unknown_model_zero_cost(self, counter: TokenCounter) -> None:
        """Model không có trong config → chi phí = 0."""
        counter.add_usage("gemini", "unknown-model", 1000, 500)

        assert counter.stats.total_tokens == 1500
        assert counter.stats.total_cost == 0.0
