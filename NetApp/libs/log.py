import logging
import pathlib
import os
from datetime import datetime


def setup_logger(script_name):
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    log_dir = pathlib.Path(os.getcwd()) / "data" / script_name / "logs"
    os.makedirs(log_dir, exist_ok=True)

    # create a formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # add a console handler, default INFO
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # add a file handler, default DEBUG
    log_filename = datetime.now().strftime(
        f"data/{script_name}/logs/{script_name}_%Y-%m-%d_%H-%M-%S.log"
    )
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
