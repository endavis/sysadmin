"""
validate ability to connect and that the config matches
"""

import logging
import pprint
import traceback

#from workbook import SpaceWorkbook
from netapp_ontap import HostConnection, utils
from netapp_ontap.resources import Disk, Cluster, Volume, Node, Aggregate

from libs.config import Config
from libs.parseargs import argp
from libs.size_utils import approximate_size_specific, convert_size

#logging.basicConfig(level=logging.DEBUG)
#utils.LOG_ALL_API_CALLS = 1

config = None

APP = None

class AppClass:
    def __init__(self, name, clusters, config):
        self.name = name
        self.cluster_details = clusters
        self.clusterdata = {}
        self.build_app()
        self.config = config
  

    def build_app(self):
        for item in self.cluster_details:
            self.clusterdata[item] = ClusterData(item, **self.cluster_details[item])

    def gather_data(self, vol_output_file=None):
        for cluster in self.clusterdata.values():
            cluster.gather_data()

class ClusterData:
    def __init__(self, clustername, **kwargs):
        self.name = clustername
        self.cluster_type = ''
        for name, value in kwargs.items():
            setattr(self, name, value)            

    def gather_data(self):
        try:
            with HostConnection(self.ip, username=config.settings['settings']['user']['name'], password=config.settings['settings']['user']['enc'], verify=False):
                cluster = Cluster()
                
                cluster.get()
                print(f'Config {self.name} connected successfully')

                if  cluster['name'] !=  self.name:
                    print(f'    Config name {self.name} does not match cluster name {cluster["name"]}')
        except:
            print(f'Could not connect to config {self.name}')
            print(traceback.format_exc())


if __name__ == '__main__':
    args = argp(description="validate netapp connectivity and config")
    config = Config(args.config_dir, debug=False)

    items = config.get_clusters(args.filters)
    # pprint.pprint(items)

    APP = AppClass('validate', items, config)
    APP.gather_data()

