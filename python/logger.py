import logging
from colorlog import ColoredFormatter


class LoggerConfig:
    def __init__(self, log_file="app.log", level=logging.DEBUG):
        self.log_file = log_file
        self.level = level
        self.setup_logging()

    def setup_logging(self):
        """Set up the logging configuration."""
        # Define log format
        log_format = "%(asctime)s - %(levelname)s - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        # Formatter for file logs (no colors)
        file_formatter = logging.Formatter(log_format, datefmt=date_format)

        # Colored Formatter for console output
        colored_formatter = ColoredFormatter(
            "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
            datefmt=date_format,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )

        # File handler setup
        file_handler = logging.FileHandler(self.log_file, mode="w")
        file_handler.setFormatter(file_formatter)

        # Console handler setup
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(colored_formatter)

        # Basic configuration with multiple handlers
        logging.basicConfig(
            level=self.level,
            format=log_format,
            datefmt=date_format,
            handlers=[file_handler, console_handler],
        )

    @staticmethod
    def get_logger(name):
        """Retrieve the logger with the given name."""
        return logging.getLogger(name)
