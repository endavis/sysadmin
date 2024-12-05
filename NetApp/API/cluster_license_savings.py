"""
This goes through all volumes and puts the data in 1 of 4 buckets

CVO HA, RW volume
CVO HA, DP volume
CVO, RW volume
CVO, DP volume
"""

import logging
import pprint
import traceback

#from workbook import SpaceWorkbook
from netapp_ontap import HostConnection, utils
from netapp_ontap.resources import Disk, Cluster, Volume, Node

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
                                             "Division",
                                             "Business Unit",                                             
                                             'Bucket',
                                             "App",
                                             "Environment",
                                             "Cloud Provider",
                                             "Tags",
                                             'Volume',
                                             'Type',
                                             "Size (TiB)",
                                             "Used (TiB)",
                                             "Percent Used",
                                             "Size if volume was 80% used (TiB)",
                                             "Savings (TiB)",
                                        "\n"])
                                )   
        self.clus_output_file = open('cluster-out.csv', 'w')
        self.clus_output_file.write(",".join(['Cluster',
                                              "Division",
                                              "Business Unit",
                                              "App",
                                              "Environment",
                                              "Cloud Provider",
                                              "Tags",
                                              "CVO - RW Provisioned Size (TiB)",
                                              "CVO - RW Potential Savings (TiB)",
                                              "CVO - RW Provisioned Size - Potential Savings",
                                              "CVO - DP Provisioned Size (TiB)",
                                              "CVO - DP Potential Savings (TiB)",
                                              "CVO - DP Provisioned Size - Potential Savings",
                                              "CVO HA - RW Provisioned Size (TiB)",
                                              "CVO HA - RW Potential Savings (TiB)",
                                              "CVO HA - RW Provisioned Size - Potential Savings",
                                              "CVO HA - DP Provisioned Size (TiB)",
                                              "CVO HA - DP Potential Savings (TiB)",
                                              "CVO HA - DP Provisioned Size - Potential Savings",
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
            if len(nodes) > 1 and nodes[0]['ha']['enabled']:
                self.cluster_type = 'CVO HA'
            else:
                self.cluster_type = 'CVO'

            buckets = {'CVO HA - DP': {'provisioned_size': 0, 'potential_savings': 0},
                       'CVO HA - RW': {'provisioned_size': 0, 'potential_savings': 0},
                       'CVO - DP': {'provisioned_size': 0, 'potential_savings': 0},
                       'CVO - RW': {'provisioned_size': 0, 'potential_savings': 0}}

            args = {}
            args['is_svm_root'] = False
            args['fields'] = ','.join(['name',
                                      'size',
                                      'aggregates',
                                      'space',
                                      'autosize.*',
                                      'guarantee',
                                      'space.*',
                                      'type',
                                    ])

            volumes = list(Volume.get_collection(**args))
            for volume in volumes:
                bucket = self.cluster_type + ' - ' + volume['type'].upper()
                size_set_as_80 = 0
                savings = 0
                try:
                    if volume['space']['percent_used'] < 80 and volume['size'] > 1073741824:
                            print(f'Here for {self.name} {volume["name"]}')
                            size_set_as_80 = volume['space']['used'] * 1.2
                            savings = volume['size'] - size_set_as_80
                    else:
                        size_set_as_80 = volume['size']
                except:
                    print(f'Error getting info for volume {volume["name"]} in cluster {self.name}')
                    print(traceback.format_exc())
                    continue                    
                APP.vol_output_file.write(",".join([self.name,
                                                 self.div,
                                                 self.bu,
                                                 bucket,
                                                 self.app,
                                                 self.env,
                                                 self.cloud,
                                                 ";".join(self.tags), 
                                                volume['name'],
                                                volume['type'].upper(),
                                                f"{approximate_size_specific(volume['size'], 'TiB', withsuffix=False)}",
                                                f"{approximate_size_specific(volume['space']['used'], 'TiB', withsuffix=False)}",
                                                f"{volume['space']['percent_used']}",
                                                f"{approximate_size_specific(size_set_as_80, 'TiB', withsuffix=False)}",
                                                f"{approximate_size_specific(savings, 'TiB', withsuffix=False)}",
                                                "\n"])
                                        )
                buckets[bucket]['provisioned_size'] += volume['size']
                buckets[bucket]['potential_savings'] += savings
                
            APP.clus_output_file.write(",".join([self.name,
                                                 self.div,
                                                 self.bu,                                                     
                                                 self.app,
                                                 self.env,
                                                 self.cloud,
                                                 ";".join(self.tags), 
                                                 f"{approximate_size_specific(buckets['CVO - RW']['provisioned_size'], 'TiB', withsuffix=False)}",
                                                 f"{approximate_size_specific(buckets['CVO - RW']['potential_savings'], 'TiB', withsuffix=False)}",
                                                 f"{approximate_size_specific(buckets['CVO - RW']['provisioned_size'] - buckets['CVO - RW']['potential_savings'], 'TiB', withsuffix=False)}",                                                
                                                 f"{approximate_size_specific(buckets['CVO - DP']['provisioned_size'], 'TiB', withsuffix=False)}",
                                                 f"{approximate_size_specific(buckets['CVO - DP']['potential_savings'], 'TiB', withsuffix=False)}",
                                                 f"{approximate_size_specific(buckets['CVO - DP']['provisioned_size'] - buckets['CVO - DP']['potential_savings'], 'TiB', withsuffix=False)}",   
                                                 f"{approximate_size_specific(buckets['CVO HA - RW']['provisioned_size'], 'TiB', withsuffix=False)}",
                                                 f"{approximate_size_specific(buckets['CVO HA - RW']['potential_savings'], 'TiB', withsuffix=False)}",
                                                 f"{approximate_size_specific(buckets['CVO HA - RW']['provisioned_size'] - buckets['CVO HA - RW']['potential_savings'], 'TiB', withsuffix=False)}",                                                
                                                 f"{approximate_size_specific(buckets['CVO HA - DP']['provisioned_size'], 'TiB', withsuffix=False)}",
                                                 f"{approximate_size_specific(buckets['CVO HA - DP']['potential_savings'], 'TiB', withsuffix=False)}",
                                                 f"{approximate_size_specific(buckets['CVO HA - DP']['provisioned_size'] - buckets['CVO HA - DP']['potential_savings'], 'TiB', withsuffix=False)}",   
                                                "\n"])
                                        )

if __name__ == '__main__':
    args = argp(description="gather volume and cluster stats, provisioned size and savings if changing to 80% and 90% autosize thresholds")
    config = Config(args.data_dir, debug=False)

    items = config.get_clusters(args.filters)

    APP = AppClass('Provisioned', items)
    APP.gather_data()

