import tomllib
import logging
import pprint

config_logger = logging.getLogger('toml-config')
# create a console handler
console_handler = logging.StreamHandler()
# set the handler's level
console_handler.setLevel(logging.DEBUG)
# create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# set the formatter for the handler
console_handler.setFormatter(formatter)
# add the handler to the logger
config_logger.addHandler(console_handler)

config = None
parsed_groups = []


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

        Eg. {'bu':'TAA', 'env':'prod', 'subapp':'POD3', 'workload':'vault'}
        """
        config_logger.debug(f"{search_terms = }")
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
    