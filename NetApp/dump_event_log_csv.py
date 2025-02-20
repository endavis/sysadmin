"""

"""
from pathlib import Path
from datetime import datetime, timezone
import logging
import pprint

from netapp_ontap import HostConnection
from netapp_ontap.resources import EmsEvent

from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger

setup_logger(Path(__file__).name)
#utils.LOG_ALL_API_CALLS = 1

file_name = Path(__file__).name

APP = None

class AppClass:
    def __init__(self, name, clusters, config):
        # print(clusters)
        self.config = config
        self.name = name
        self.cluster_details = clusters
        self.cluster_data = {}
        self.output = []
        self.output.append('Node,Time,Event,Severity,Message')

        self.build_app()

    def build_app(self):
        for item in self.cluster_details:
            self.cluster_data[item] = ClusterData(item, self, **self.cluster_details[item])

    def go(self):
        for cluster in self.cluster_data.values():
            cluster.gather_data()
            cluster.process_data()

        with open('output/ems_output.csv', 'w') as output:
            for line in self.output:
                if line:
                    output.write(line + '\n')

class ClusterData:
    def __init__(self, clustername, app_instance, **kwargs):
        self.name = clustername
        self.cluster_type = ''
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.fetched_data = {}
        self.app_instance = app_instance

    def gather_data(self):
        self.fetched_data['emsevents'] = []

        with HostConnection(self.ip, username='cvomon', password=config.settings['users']['cvomon']['enc'], verify=False):
            for event in EmsEvent.get_collection(order_by="time",fields="*"):
                self.fetched_data['emsevents'].append(event)


    def process_data(self):
        # Event Structure
        # {'_links': {'self': {'href': '/api/support/ems/events/somenode-02/1875713'}},
        # 'index': 1875713,
        # 'log_message': 'vsa.scheduledEvent.update: Cloud provider event status update '
        #                 'for node "somenode-02". ID: '
        #                 'CC5E4432-77F8-4218-A1C9-18B0623CB04B. Type: freeze. Status: '
        #                 'complete.',
        # 'message': {'name': 'vsa.scheduledEvent.update', 'severity': 'notice'},
        # 'node': {'_links': {'self': {'href': '/api/cluster/nodes/84300338-1d81-11ea-986b-000d3aa4b387'}},
        #         'name': 'somenode-02',
        #         'uuid': '84300338-1d81-11ea-986b-000d3aa4b387'},
        # 'parameters': [{'name': 'detail', 'value': 'status update'},
        #                 {'name': 'node', 'value': 'somenode-02'},
        #                 {'name': 'event_id',
        #                 'value': 'CC5E4432-77F8-4218-A1C9-18B0623CB04B'},
        #                 {'name': 'event_type', 'value': 'freeze'},
        #                 {'name': 'status', 'value': 'complete'}],
        # 'source': 'mgwd',
        # 'time': '2025-02-18T23:13:32+00:00'}
        for event in self.fetched_data['emsevents']:

            csv_output = [
                event['node']['name'],
                f"{event['time']}",
                event['message']['name'],
                event['message']['severity'],
                event['log_message'].replace(f"{event['message']['name']}: ", "").replace(',', ';').replace('\n', '').strip()
            ]
            csv_line = ",".join(csv_output)
            if csv_line != ",,,,":
                self.app_instance.output.append(",".join(csv_output))



if __name__ == '__main__':
    args = argp(description="check clusters for licensing issues")
    config = Config(args.data_dir)

    items = config.get_clusters(args.filter)

    APP = AppClass('dump_event_log_csv', items, config)
    APP.go()

