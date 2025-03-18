"""
This goes through all volumes and puts the data in 1 of 4 buckets

CVO HA, RW volume
CVO HA, DP volume
CVO, RW volume
CVO, DP volume
"""

import logging
import pprint

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
    def __init__(self, name, clusters):
        self.name = name
        self.cluster_details = clusters
        self.clusterdata = {}
        self.build_app()
        self.vol_output_file = open('vol-out.csv', 'w')
        self.vol_output_file.write(",".join(['Cluster',
                                             "App",
                                             "Sub App",
                                             "Environment",
                                             "Tags",
                                             'Volume',
                                             'Type',
                                             "User Data Space Used (TiB)",
                                        "\n"])
                                )   
        self.clus_output_file = open('cluster-out.csv', 'w')
        self.clus_output_file.write(",".join(['Cluster',
                                              "App",
                                              "Sub App", 
                                              "Environment",
                                              "Tags",
                                              "User Data Space Used (TiB)",
                                              "\n"])
                                )   

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
        with HostConnection(self.ip, username=config.settings['settings']['user']['name'], password=config.settings['settings']['user']['enc'], verify=False):
            cluster = Cluster()
            
            cluster.get()

            nodes = list(Node.get_collection(fields="ha"))

            total_user_data = 0

            volume_args = {}
            volume_args['is_svm_root'] = False
            volume_args['fields'] = ','.join(['name',
                                      'size',
                                      'aggregates',
                                      'autosize.*',
                                      'guarantee',
                                      'space.*',
                                      'type',
                                    ])

            volumes = list(Volume.get_collection(**volume_args))
            for volume in volumes:
                # if volume['name'] == "LTTY2022_CU010":
                #      pprint.pprint(volume._last_state)
                total_user_data += volume['space']['user_data']
                APP.vol_output_file.write(",".join([self.name,
                                                 self.app,
                                                 self.subapp,
                                                 self.env,
                                                 ";".join(self.tags), 
                                                volume['name'],
                                                volume['type'].upper(),
                                                f"{approximate_size_specific(volume['space']['user_data'], 'TiB', withsuffix=False)}",
                                                "\n"])
                                        )
                
            APP.clus_output_file.write(",".join([self.name,
                                                 self.app,
                                                 self.subapp,
                                                 self.env,
                                                 ";".join(self.tags), 
                                                 f"{approximate_size_specific(total_user_data, 'TiB', withsuffix=False)}",
                                                "\n"])
                                        )

if __name__ == '__main__':
    args = argp(description="gather volume and cluster stats, provisioned size and savings if changing to 80% and 90% autosize thresholds")
    config = Config(args.config_dir, debug=False)

    items = config.get_clusters(args.filters)

    APP = AppClass('Provisioned', items)
    APP.gather_data()

