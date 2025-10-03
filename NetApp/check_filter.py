"""

"""
from pathlib import Path
import logging
import pprint

from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger

setup_logger()
#utils.LOG_ALL_API_CALLS = 1

script_name = Path(__file__).stem

APP = None

class AppClass:
    def __init__(self, name, clusters, config):
        # print(clusters)
        self.config = config
        self.name = name
        self.cluster_details = clusters
        self.license_issues = []
        self.cluster_data = {}
        self.license_issues = []

        self.build_app()

    def build_app(self):
        logging.info("Filter returned the following clusters:")
        for item in self.cluster_details:
            logging.info(f"  {item}")


if __name__ == '__main__':

    args = argp(script_name=script_name, description="check clusters for licensing issues")
    config = Config(args.config_dir, args.output_dir)

    items = config.get_clusters(args.filter)

    APP = AppClass(script_name, items, config)

