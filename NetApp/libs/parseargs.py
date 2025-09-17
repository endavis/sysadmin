
import argparse
import json
import pathlib
import logging

file_name = pathlib.Path(__file__).name

class argp:
    def __init__(self, script_name='unknown', description="default description", parse=True):

        self.description = description

        self.parser = argparse.ArgumentParser(description=self.description)
        self.parser.add_argument('-c', '--config_dir', type=str, help="configuration directory", default='config')
        self.parser.add_argument('-f', '--filter', type=str, help="""filter: Example: -f '{"bu":"Business", "env":"Prod", "tags":"active"}'""")
        self.parser.add_argument('-de', '--debug', type=bool, default=False, help="""turn on debugging, default False""")
        self.parser.add_argument('-o', '--output_dir', type=str, help="output directory", default=f"output/{script_name}")

        if parse:
            self.parse()

    def parse(self):
        self.args = self.parser.parse_args(namespace=self)

        if self.filter:
            logging.debug(f"{file_name} : filter before conversion: {self.filter = }")
            converted_filter = self.parse_json(self.filter)
            logging.debug(f"{file_name} : After conversion: {type(converted_filter) = } {converted_filter = }")
            self.filter = converted_filter
        else:
            self.filter = ''

        if self.debug:
            for handler in logging.getLogger().handlers:
                handler.setLevel(logging.DEBUG)

    def parse_json(self, json_string):
        try:
            # Convert the JSON string to a dictionary
            arg_dict = json.loads(json_string)
            return arg_dict
        except json.JSONDecodeError as e:
            logging.error(f"{file_name} : Error decoding JSON: {e}")

        return None

