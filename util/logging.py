import logging
import os
from pathlib import Path
from datetime import datetime


class CleanFormatter(logging.Formatter):
    """Custom formatter for cleaner, more elegant log output with minimal display"""

    COLORS = {
        'INFO': '\033[0;32m',
        'RESET': '\033[0m'
    }

    TERMINAL_VISIBLE_PATTERNS = [
        "Processing query",
        "Query processed in",
        "Agent is thinking"
    ]

    def format(self, record):
        log_msg = record.getMessage()

        if record.levelname in ['WARNING', 'ERROR']:
            return None

        if record.funcName == 'log_function_call':
            return None

        msg_lower = log_msg.lower()
        visible = any(
            pattern.lower() in msg_lower for pattern in self.TERMINAL_VISIBLE_PATTERNS)

        if not visible:
            return None

        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        if record.levelname == 'INFO':
            if log_msg.startswith('SUCCESS:'):
                log_msg = log_msg.replace('SUCCESS:', '✓')
                return f"{color}{log_msg}{reset}"
            return f"{color}{log_msg}{reset}"

        return None


class EmptyFilter(logging.Filter):
    """Filter out empty log messages to prevent blank lines in console"""

    def filter(self, record):
        return bool(record.getMessage().strip())


def setup_logging():
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"lyne_{timestamp}.log"

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CleanFormatter())
    console_handler.addFilter(EmptyFilter())

    console_handler.setLevel(logging.CRITICAL)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )


def get_logger(name):
    if not logging.getLogger().handlers:
        setup_logging()
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger


def log_function_call(func_name, params, logger):
    logger.info(f"{func_name} called with params: {params}")


def log_error(error, message, logger):
    """Log error message (goes to file only)"""
    logger.error(f"{message}: {error}")


def log_success(message, logger):
    """Log success message (goes to file only, may show in terminal for important messages)"""
    logger.info(f"SUCCESS: {message}")


def log_info(message, logger):
    """Log info message (goes to file only)"""
    logger.info(message)


def log_warning(message, logger):
    """Log warning message (goes to file only)"""
    logger.warning(message)
