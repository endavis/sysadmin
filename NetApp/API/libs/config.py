"""
# the below will check each item
-f '{"div":"div1"}' '{"bu":"bu1"}' '{"tags":"tag1"}'
# the below will check if a tag matches one of the tags in the list
-f '{"div":"div1"}' '{"bu":"bu1"}' '{"tags":["tag1", "tag2"]}'
# the below will only return items that have both tags
-f '{"div":"div1"}' '{"bu":"bu1"}' '{"tags":"tag1"} '{"tags":"tag2"}'
"""

import tomllib
import logging
import pprint
from .log import setup_logger

config_logger = setup_logger('toml-config')

class Config:
    def __init__(self, config_file, debug=False):
        self.username = None
        self.enc = None
        self.config = None
        self.config_file = config_file
        if debug:
            print('toml-config: setting logging to debug')
            config_logger.setLevel(logging.DEBUG)
        self.parse_config()

    def parse_config(self):
        with open(self.config_file, "rb") as f:
            self.config = tomllib.load(f)
            config_logger.debug(f"config read: {pprint.pformat(self.config)}")

        self.username = self.config['default']['name']
        self.enc = self.config['default']['enc']

    def search(self, search_terms):
        """
        search for clusters that match the given fields
        each param should be a dictionary with field and value

        this is case insensitive
        """
        config_logger.debug(f"{search_terms = }")
        if not search_terms:
            return self.config['cluster-data'].copy()
        results = {}
        for cluster in self.config['cluster-data']:
            cluster_details = self.config['cluster-data'][cluster]
            config_logger.debug(f"{cluster_details = }")
            result_check = []
            for item in search_terms:
                config_logger.debug(f"{item = }")
                for k,v in item.items():
                    config_logger.debug(f"{k = } {v = }")
                    if isinstance(cluster_details[k.lower()], list):
                        if isinstance(v, list):
                            found = False
                            for i in v:
                                if i in cluster_details[k.lower()]:
                                    found = True
                            config_logger.debug(f"checking list in list: {found}")
                            result_check.append(found)
                            continue
                        else:
                            if v in cluster_details[k.lower()]:
                                config_logger.debug('cluster_details[k.lower()] is a list and v is in it')
                                result_check.append(True)
                                continue
                    else:
                        if v == cluster_details[k.lower()].lower():
                            config_logger.debug('v == cluster_details[k.lower()]')
                            result_check.append(True)
                            continue
                        if v in cluster_details[k.lower()]:
                            config_logger.debug('v in cluster_details[k.lower()]')
                            result_check.append(True)
                            continue
                    config_logger.debug("unsuccessful")
                    result_check.append(False)

            if all(result_check):
                results[cluster] = cluster_details
        return results
    