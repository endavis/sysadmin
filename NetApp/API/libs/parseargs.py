
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
        self.parser.add_argument('-c', '--config', type=str, help="config file", required=True)
        self.parser.add_argument('-f', '--filters', nargs='+', help="""filters: Example: -f '{"div":"div1"}' '{"bu":"bu1"}' '{"tags":"tag1"}'""")        
    
        self.args = self.parser.parse_args(namespace=self)

        if self.filters:
            argp_logger.debug(f"All filters before conversion: {self.filters = }")
            new_filters = []
            for filter in self.filters:
                argp_logger.debug(f"Before conversion: {type(filter) = } {filter = }")
                converted_filter = self.parse_json(filter)
                if converted_filter:
                    new_filters.append(converted_filter)
                    argp_logger.debug(f"After conversion: {type(converted_filter) = } {converted_filter = }")
            self.filters = new_filters
            argp_logger.debug(f"All filters after converstion: {self.filters = }")
        else:
            self.filters = []

    def parse_json(self, json_string):
        try:
            # Convert the JSON string to a dictionary
            arg_dict = json.loads(json_string)
            return arg_dict
        except json.JSONDecodeError as e:
            argp_logger.error(f"Error decoding JSON: {e}")
            
        return None

