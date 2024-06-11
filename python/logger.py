import logging

class LoggerConfig:
    def __init__(self, log_file='app.log', level=logging.DEBUG):
        self.log_file = log_file
        self.level = level
        self.setup_logging()

    def setup_logging(self):
        """Set up the logging configuration."""
        logging.basicConfig(level=self.level,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            handlers=[
                                logging.FileHandler(self.log_file, mode='w'),
                                logging.StreamHandler()
                            ])

    @staticmethod
    def get_logger(name):
        """Retrieve the logger with the given name."""
        return logging.getLogger(name)