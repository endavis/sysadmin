
import argparse
import json
from .log import setup_logger

argp_logger = setup_logger('argp')

class argp:
    def __init__(self, description="default description", debug=False):

        if debug:
            argp_logger.setLevel('DEBUG')
        self.description = description

        self.parser = argparse.ArgumentParser(description=self.description)
        self.parser.add_argument('-d', '--data_dir', type=str, help="config file", default='data')
        self.parser.add_argument('-f', '--filter', type=str, help="""filter: Example: -f '{"bu":"Business", "env":"Prod", "tags":"active"}'""")        
    
        self.args = self.parser.parse_args(namespace=self)

        if self.filter:
            argp_logger.debug(f"filter before conversion: {self.filter = }")
            converted_filter = self.parse_json(self.filter)
            argp_logger.debug(f"After conversion: {type(converted_filter) = } {converted_filter = }")
            self.filter = converted_filter
        else:
            self.filter = ''

    def parse_json(self, json_string):
        try:
            # Convert the JSON string to a dictionary
            arg_dict = json.loads(json_string)
            return arg_dict
        except json.JSONDecodeError as e:
            argp_logger.error(f"Error decoding JSON: {e}")
            
        return None

