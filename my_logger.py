import os
import logging


LOG_ROOT = '/logs/'
log_path = os.path.abspath(os.curdir) + LOG_ROOT
log_path_exist = os.path.exists(log_path)
if not log_path_exist:
    os.makedirs(log_path)

class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s [%(name)s] [%(levelname)-5.5s] [line:%(lineno)d] %(message)s"

    # format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def log(name):
    logging.basicConfig(level=logging.INFO,
                        filename=f'{log_path}last.log',
                        filemode='w',
                        format='%(asctime)s - %(levelname)s - %(message)s'
                        )
    logger = logging.getLogger(name)
    main_handler = logging.FileHandler(f'{log_path}{name}.log')
    main_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main_handler.setFormatter(main_formatter)
    logger.addHandler(main_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    # console_handler.setFormatter(console_formatter)
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)

    return logger