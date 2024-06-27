import logging

def setup_logger(loggername):
    temp_logger = logging.getLogger(loggername)
    # create a console handler
    console_handler = logging.StreamHandler()
    # set the handler's level
    console_handler.setLevel(logging.DEBUG)
    # create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # set the formatter for the handler
    console_handler.setFormatter(formatter)
    # add the handler to the logger
    temp_logger.addHandler(console_handler)

    return temp_logger
