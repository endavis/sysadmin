"""Module to parse command line arguments and set specific flags."""

import argparse
import json
import pathlib
import logging
import os

import psutil

file_name = pathlib.Path(__file__).name


class argp:
    """Wraps argparse to add default arguments."""

    def __init__(
        self, script_name="unknown", description="default description", parse=True
    ):
        """Initialize the parser with common arguments."""
        self.description = description
        self.pid = os.getpid()
        self.cmd_line = psutil.Process(self.pid).cmdline()
        self.environ = psutil.Process(self.pid).environ()

        logging.info(f"Command line '{self.cmd_line}'")
        logging.debug(f"Working directory: {psutil.Process(self.pid).cwd()}")
        logging.debug("Environment:")
        for item in self.environ:
            logging.debug(f"    '{item}':'{self.environ[item]}'")

        self.parser = argparse.ArgumentParser(description=self.description)
        self.parser.add_argument(
            "-c",
            "--config_dir",
            type=str,
            help="configuration directory",
            default="config",
        )
        self.parser.add_argument(
            "-f",
            "--filter",
            type=str,
            help="""filter: Example: -f '{"bu":"Business","""
            """ "env":"Prod", "tags":"active"}'""",
        )
        self.parser.add_argument(
            "-de",
            "--debug",
            type=bool,
            default=False,
            help="""turn on debugging, default False""",
        )
        self.parser.add_argument(
            "-o",
            "--output_dir",
            type=str,
            help="output directory",
            default=f"output/{script_name}",
        )

        if parse:
            self.parse()

    def parse(self):
        """Parse the arguments and set the filter and debug flag."""
        self.args = self.parser.parse_args(namespace=self)

        if self.args.filter:  # pyright: ignore[reportAttributeAccessIssue]
            logging.debug(
                f"{file_name} : filter before conversion: {self.args.filter = }"  # pyright: ignore[reportAttributeAccessIssue]
            )
            converted_filter = self.parse_json(
                self.args.filter  # pyright: ignore[reportAttributeAccessIssue]
            )
            logging.debug(
                f"{file_name} : After conversion: {type(converted_filter) = }"
                f" {converted_filter = }"
            )
            self.args.filter = (  # pyright: ignore[reportAttributeAccessIssue]
                converted_filter
            )
        else:
            self.args.filter = ""  # pyright: ignore[reportAttributeAccessIssue]

        if self.args.debug:  # pyright: ignore[reportAttributeAccessIssue]
            for handler in logging.getLogger().handlers:
                handler.setLevel(logging.DEBUG)

    def parse_json(self, json_string):
        """Parse a json string.

        :param json_string: The json string to parse
        """
        try:
            # Convert the JSON string to a dictionary
            arg_dict = json.loads(json_string)
            return arg_dict
        except json.JSONDecodeError as e:
            logging.error(f"{file_name} : Error decoding JSON: {e}")

        return None
