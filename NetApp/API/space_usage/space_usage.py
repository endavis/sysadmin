import logging
import configparser
import pprint

from workbook import SpaceWorkbook
from netapp_ontap import HostConnection, utils
from netapp_ontap.resources import FileInfo, CifsShare, UnixUser, Svm, Volume, Cluster

from size_utils import approximate_size, convert_size

logging.basicConfig(level=logging.DEBUG)
#utils.LOG_ALL_API_CALLS = 1

config = configparser.ConfigParser()
config.optionxform = str
config.read('config.ini')

username = config['default']['name']
enc = config['default']['enc']

# ZUSCULTAXCST010
API_IP = '192.168.1.1'

letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

SWB = SpaceWorkbook(config['default']['output-file'])

APPS = {}

class App:
    def __init__(self, name):
        self.name = name
        self.environments = {}
        self.build_app()

    def build_app(self):
        envs = config.options(self.name)
        for item in envs:
            self.add_environment(item)

    def add_environment(self, environment_name):
        self.environments[environment_name] = {}
        section = f'{self.name}-{environment_name}'
        clusters = config.options(section)
        for cluster in clusters:
            self.environments[environment_name][cluster] = ClusterData(self.name, environment_name, cluster, config.get(section, cluster))

    def gather_data(self):
        for environment in self.environments:
            for cluster in self.environments[environment].values():
                cluster.gather_data()

class ClusterData:
    def __init__(self, app, environment, name, ip):
        self.app = app
        self.environment = environment
        self.name = name
        self.ip = ip

    def gather_data(self):
        with HostConnection(self.ip, username=username, password=enc, verify=False):
            cluster = Cluster()
            
            cluster.get()
            cluster_data = SWB.addcluster(self.app, self.environment, cluster['name'])
            resource = Svm.find(name="svm*")
            args = {}
            args['svm.name'] = resource['name']
            args['is_svm_root'] = False
            args['fields'] = 'aggregates.name,space.footprint,space.capacity_tier_footprint,space.performance_tier_footprint,space.user_data'
            volumes = Volume.get_collection(**args)
            for volume in volumes:
                if 'tax' in volume['aggregates'][0]['name'].lower():
                    vtype = 'TAX'
                elif 'doc' in volume['aggregates'][0]['name'].lower():
                    vtype = 'DOCUMENT'
                elif 'app' in volume['aggregates'][0]['name'].lower():
                    vtype = 'APP'
                else:
                    vtype = 'UNKNOWN'
                cluster_data.addvolume(volume['name'], vtype, approximate_size(volume["space"]["performance_tier_footprint"] + volume["space"]["capacity_tier_footprint"], 
                                                                                newsuffix='GB', withsuffix=False),            
                                        approximate_size(volume["space"]["performance_tier_footprint"], newsuffix='GB', withsuffix=False),
                                        approximate_size(volume["space"]["capacity_tier_footprint"], newsuffix='GB', withsuffix=False))   

if __name__ == '__main__':
    apps = config.options('Apps')
    for app in apps:
        APPS[app] = App(app)
        APPS[app].gather_data()

    SWB.close()
