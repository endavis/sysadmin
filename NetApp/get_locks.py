"""

"""
import pprint
import logging
import sys
from datetime import datetime

#from workbook import SpaceWorkbook
from netapp_ontap import HostConnection, utils
from netapp_ontap.resources import ClientLock, Volume
from openpyxl import Workbook

from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger


logger = setup_logger()
#utils.LOG_ALL_API_CALLS = 1

APP = None

class AppClass:
    def __init__(self, name, clusters, config):
        self.config = config
        self.name = name
        self.cluster_details = clusters
        self.clusterdata = {}
        #self.volume_name = 'PDECREATE'  
        self.volume_name = 'PDECREATE_NC111'      
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = self.volume_name
        #Volume	Protocol	Type	Path	Lock	State	IP address
        self.ws.append(["Volume","Protocol","Type","Path","Lock","State","IP address"])
        self.build_app()

    def build_app(self):
        for item in self.cluster_details:
            self.clusterdata[item] = ClusterData(item, self, **self.cluster_details[item])

    def go(self):
        for cluster in self.clusterdata.values():
            cluster.gather_data()
            cluster.output_data()

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        filename = config.output_dir / f"locks_{self.volume_name}_{timestamp}.xlsx"
        if self.ws.max_row > 1:
            logging.info(f"Locks found: {self.ws.max_row - 1}")
            self.wb.save(filename)
        else:
            logging.info("No locks found")

class ClusterData:
    def __init__(self, clustername: str, app_instance: AppClass, **kwargs):
        self.name = clustername
        self.cluster_type = ''
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.fetched_data = {}
        self.app_instance = app_instance

    def gather_data(self):
        with HostConnection(self.ip, username='cvomon', password=config.settings['users']['cvomon']['enc'], verify=False):
            volumes = list(Volume.get_collection(name=self.app_instance.volume_name))
            
            if len(volumes) == 1:
                volume_uuid = volumes[0].uuid
            else:
                logging.error("More than one volume found")
                sys.exit(1)

            self.fetched_data['locks'] = []
            for lock in ClientLock.get_collection(**{"fields":"*", "volume.uuid":volume_uuid}):
                self.fetched_data['locks'].append(lock.to_dict())
       

    def output_data(self):
        for item in self.fetched_data['locks']:
            #'Volume,Protocol,Type,Path,Share Lock,Oplock Level,State,IP address'

            try:
                if item['type'] == 'share_level':
                    self.app_instance.ws.append([item['volume']['name'],item['path'],item['protocol'],item['type'],f"{item['share_lock']}",item['state'],item['client_address']])
                else:
                    if item['type'] == 'op_lock':
                        self.app_instance.ws.append([item['volume']['name'],item['path'],item['protocol'],item['type'],f"{item['oplock_level']}",item['state'],item['client_address']])
                    else:
                        logging.info(f"Unknown type for {item}")

            except Exception as e:
                logging.error(f"Lock error {e}")
                pprint.pprint(item)

if __name__ == '__main__':
    args = argp(description="build html page of endpoints and mostly static information")
    config = Config(args.config_dir)

    items = config.get_clusters(args.filter)
    # aiqums = config.search('aiqums', {'bu':'PUMA'})
    # pprint.pprint(aiqums)
    # connectors = config.search('connectors', {'bu':'PUMA'})
    # pprint.pprint(connectors)

    # pprint.pprint(items)

    APP = AppClass('html', items, config)
    APP.go()

