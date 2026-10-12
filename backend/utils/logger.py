"""Thread-safe logging queue handler for real-time streaming logs."""

import logging
import queue
from typing import List, Optional

# Thread-safe queue to pass log messages to REST API or UI consumers
ui_log_queue: queue.Queue = queue.Queue()


class EndpointFilter(logging.Filter):
    """Filter to suppress repetitive high-frequency polling access logs (e.g. /health)."""

    def __init__(self, filter_endpoints: Optional[List[str]] = None) -> None:
        super().__init__()
        self.filter_endpoints = filter_endpoints or ["/api/v1/health", "/health"]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for ep in self.filter_endpoints:
            if f"GET {ep} " in msg or f'"{ep}"' in msg:
                return False
        return True


class UIQueueHandler(logging.Handler):
    """Custom logging handler that pushes formatted records to a thread-safe queue."""

    def emit(self, record: logging.LogRecord) -> None:
        """Formats and enqueues log record.

        Args:
            record (logging.LogRecord): Log record instance.
        """
        try:
            msg = self.format(record)
            ui_log_queue.put_nowait(msg)
        except Exception:
            self.handleError(record)


def setup_ui_logger() -> None:
    """Attaches UIQueueHandler to root logger and unifies Uvicorn logging formatting."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    for h in logger.handlers:
        h.setFormatter(formatter)

    if not any(isinstance(h, UIQueueHandler) for h in logger.handlers):
        ui_handler = UIQueueHandler()
        ui_handler.setFormatter(formatter)
        logger.addHandler(ui_handler)

    for u_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        u_logger = logging.getLogger(u_logger_name)
        u_logger.setLevel(logging.INFO)
        for h in u_logger.handlers:
            h.setFormatter(formatter)

    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, EndpointFilter) for f in access_logger.filters):
        access_logger.addFilter(EndpointFilter())


def consume_logs_from_queue(max_items: int = 100) -> List[str]:
    """Consumes and returns pending log messages from queue.

    Args:
        max_items (int): Maximum messages to pop.

    Returns:
        List[str]: Formatted log messages list.
    """
    messages: List[str] = []
    while not ui_log_queue.empty() and len(messages) < max_items:
        try:
            msg = ui_log_queue.get_nowait()
            messages.append(msg)
        except queue.Empty:
            break
    return messages
