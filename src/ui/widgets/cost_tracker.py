"""Backward-compatible alias for the old CostTracker name."""

from src.ui.widgets.processing_controls import ProcessingControls


class CostTracker(ProcessingControls):
    """Deprecated name kept for existing imports and tests."""
