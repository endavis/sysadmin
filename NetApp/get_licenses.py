"""

"""
import pathlib
import pprint
import datetime
import logging

from yattag import Doc, indent

#from workbook import SpaceWorkbook
from netapp_ontap import HostConnection, utils
from netapp_ontap.resources import Cluster, Node, Svm, IpInterface, CifsService, LicensePackage

from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger


logger = setup_logger()

script_name = pathlib.Path(__file__).stem

#utils.LOG_ALL_API_CALLS = 1

APP = None

class AppClass:
    def __init__(self, name, clusters, config):
        self.config = config
        self.name = name
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.filename = self.config.output_dir / f"{script_name}_{timestamp}.csv"
        self.cluster_details = clusters
        self.clusterdata = {}
        self.divisions = {}
        self.counts = {}
        self.counts['ha'] = 0
        self.counts['sn'] = 0
        self.counts['aiqums'] = 0
        self.counts['connectors'] = 0
        self.button_ids =[]
        self.output = []
        self.output.append('Cluster,License Description,Node,Serial #,Expiration')

        self.doc, self.tag, self.text = Doc().tagtext()
        self.build_app()

    def build_app(self):
        self.counts['aiqums'] = self.config.count('aiqums', 'ip')
        self.counts['connectors'] = self.config.count('connectors', 'ip')
        for item in self.cluster_details:
            self.clusterdata[item] = ClusterData(item, self, **self.cluster_details[item])
            cluster = self.clusterdata[item]

    def go(self):
        for cluster in self.clusterdata.values():
            cluster.gather_data()
            cluster.output_data()

        with open(self.filename, 'w') as licenseout:
            for line in self.output:
                licenseout.write(line + '\n')

        logging.info(f"Output save to {self.filename}")


class ClusterData:
    def __init__(self, clustername, app_instance, **kwargs):
        self.name = clustername
        self.cluster_type = ''
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.fetched_data = {}
        self.app_instance = app_instance
        # self.gather_data()

    def gather_data(self):
        logging.info(f"Gathering info for {self.name}")
        user, enc = self.app_instance.config.get_user('clusters', self.name)
        with HostConnection(self.ip, username=user, password=enc, verify=False):
            self.fetched_data['licenses'] = []
            for license in LicensePackage.get_collection(fields="*"):
                self.fetched_data['licenses'].append(license.to_dict())

    def output_data(self):
        foundcloud = False
        for license in self.fetched_data['licenses']:
            if license['description'] == 'Cloud ONTAP License':
                foundcloud = True
            for item in license['licenses']:
                if 'expiry_time' in item and item['owner'] != 'none':
                    self.app_instance.output.append(f"{self.name},{license['description']},{item['owner']},'{item['serial_number']},{item['expiry_time']}")

        if not foundcloud:
            self.app_instance.output.append(f"{self.name},No Cloud license found")

if __name__ == '__main__':
    args = argp(script_name=script_name, description="output licenses to a csv")
    config = Config(args.config_dir, args.output_dir)

    items = config.get_clusters(args.filter)
    # aiqums = config.search('aiqums', {'bu':'PUMA'})
    # pprint.pprint(aiqums)
    # connectors = config.search('connectors', {'bu':'PUMA'})
    # pprint.pprint(connectors)

    # pprint.pprint(items)

    APP = AppClass(script_name, items, config)
    APP.go()

