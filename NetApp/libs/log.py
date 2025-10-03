import pathlib
import logging
import sys
from datetime import datetime

def setup_logger():
    loggername = pathlib.Path(sys.argv[0]).stem
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # create a formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # add a console handler, default INFO
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # add a file handler, default DEBUG
    log_filename = datetime.now().strftime(f'logs/{loggername}_%Y-%m-%d_%H-%M-%S.log')
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
