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
        self.license_issues = []
        self.cluster_data = {}
        self.license_issues = []

        self.build_app()

    def build_app(self):
        for item in self.cluster_details:
            self.cluster_data[item] = ClusterData(item, self, **self.cluster_details[item])

    def go(self):
        for cluster in self.cluster_data.values():
            cluster.gather_data()
            cluster.process_data()


class ClusterData:
    def __init__(self, clustername, app_instance, **kwargs):
        self.name = clustername
        self.cluster_type = ''
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.fetched_data = {}
        self.app_instance = app_instance
        self.required_timings = [
                    'az maint not before',
                    'az maint scheduled',
                    'az maint started',
                    'az maint complete',
                    'node takeover complete',
                    'node reboot starts',
                    'node reboot complete',
                    'node ready for giveback',
                    'node giveback starts',
                    'node giveback complete',
        ]

    def empty_azevent(self):
        return {'event_id':'Unknown',
                'timing':{}}

                # 'timing':{
                #     'az maint not before': 'Unknown',
                #     'az maint scheduled' : 'Unknown',
                #     'az maint started' : 'Unknown',
                #     'az maint complete' : 'Unknown',
                #     'node takeover complete' : 'Unknown',
                #     'node reboot starts' : 'Unknown',
                #     'node reboot complete' : 'Unknown',
                #     'node ready for giveback' : 'Unknown',
                #     'node giveback starts' : 'Unknown',
                #     'node giveback complete' : 'Unknown',
                # }}

    def gather_data(self):
        self.fetched_data['azmaints'] = {}
        azevent_dict = self.empty_azevent()

        with HostConnection(self.ip, username='cvomon', password=config.settings['users']['cvomon']['enc'], verify=False):
            # Event Structure
            # {'_links': {'self': {'href': '/api/support/ems/events/somenode-02/1875713'}},
            # 'index': 1875713,
            # 'log_message': 'vsa.scheduledEvent.update: Cloud provider event status update '
            #                 'for node "somenode-02". ID: '
            #                 'CC5E4432-77F8-4218-A1C9-18B0623CB04B. Type: freeze. Status: '
            #                 'complete.',
            # 'message': {'name': 'vsa.scheduledEvent.update', 'severity': 'notice'},
            # 'node': {'_links': {'self': {'href': '/api/cluster/nodes/94300338-1d81-11ea-986b-000d3aa4b387'}},
            #         'name': 'somenode-02',
            #         'uuid': '94300338-1d81-11ea-986b-000d3aa4b387'},
            # 'parameters': [{'name': 'detail', 'value': 'status update'},
            #                 {'name': 'node', 'value': 'somenode-02'},
            #                 {'name': 'event_id',
            #                 'value': 'CC5E4432-77F8-4218-A1C9-18B0623CB04B'},
            #                 {'name': 'event_type', 'value': 'freeze'},
            #                 {'name': 'status', 'value': 'complete'}],
            # 'source': 'mgwd',
            # 'time': '2025-02-18T23:13:32+00:00'}

            # Timeline:
            # azevent scheduled
            #       2/18/2025 22:42:35  somenode-02
            #                         ALERT         vsa.scheduledEvent.scheduled: Cloud provider event scheduled from: Platform, out: 9 for node "somenode-02". ID: CC5E4432-77F8-4218-A1C9-18B0623CB04B. Type: freeze. Not before: 2/18/2025 22:56:56.
            # takeover done with event sfo.takenOver.relocDone
            #       2/18/2025 22:43:09  somenode-02
            #                         INFORMATIONAL sfo.takenOver.relocDone: partner_name="somenode-01", partner_sysid="0101010101", relocation_status="0"
            # reboot start: kern.shutdown
            #       2/18/2025 22:43:40  somenode-02
            #                         NOTICE        kern.shutdown: System shut down because : "D-blade Shutdown".
            # reboot finish: mgr.boot.disk_done
            #       2/18/2025 23:12:43  somenode-02
            #                         INFORMATIONAL mgr.boot.disk_done: NetApp Release 9.00.0P1 boot complete. Last disk update written at Tue Feb 18 23:12:34 GMT 2025
            # starts waiting for giveback: cf.fsm.takeoverOfPartnerEnabled
            #       2/18/2025 23:12:50  somenode-02
            #                         NOTICE        cf.fsm.takeoverOfPartnerEnabled: Failover monitor: takeover of somenode-01 enabled
            # azevent starts somewhere between scheduled and complete
            #       2/18/2025 23:13:29  somenode-02
            #                         NOTICE        vsa.scheduledEvent.update: Cloud provider event status update for node "somenode-02". ID: CC5E4432-77F8-4218-A1C9-18B0623CB04B. Type: freeze. Status: started.
            # azevent complete
            #       2/18/2025 23:13:32  somenode-02
            #                         NOTICE        vsa.scheduledEvent.update: Cloud provider event status update for node "somenode-02". ID: CC5E4432-77F8-4218-A1C9-18B0623CB04B. Type: freeze. Status: complete.
            # failback starts:
            #       2/18/2025 23:13:39  somenode-02
            #                         INFORMATIONAL clam.valid.config: Local node (name=somenode-02, id=1001) is operating in a suitable configuration for providing CLAM functionality.
            # failback complete:
            #       2/18/2025 23:17:08  somenode-02
            #                      NOTICE        callhome.reboot.giveback: Call home for REBOOT (after giveback)
            events_to_get = ['vsa.scheduled*',
                             'sfo.takenOver.relocDone*',
                             'vifmgr.lifmoved.nodedown',
                             'kern.shutdown*',
                             'mgr.boot.disk_done',
                             'cf.fsm.takeoverOfPartnerEnabled',
                             'clam.valid.config',
                             'callhome.reboot.giveback']
            for emsevent in EmsEvent.get_collection(**{"message.name": ",".join(events_to_get)}, order_by="time",fields="*"):
                # pprint.pprint(emsevent.to_dict())

                if 'vsa.scheduled' in emsevent['message']['name']:
                    azevent_id = next((item['value'] for item in emsevent['parameters'] if item['name'] == 'event_id'), None)
                    event_type = next((item['value'] for item in emsevent['parameters'] if item['name'] == 'event_type'), None)
                    node = next((item['value'] for item in emsevent['parameters'] if item['name'] == 'node'), None)
                    status = next((item['value'] for item in emsevent['parameters'] if  item['name'] == 'status'), None)
                    not_before_time = next((item['value'] for item in emsevent['parameters'] if item['name'] == 'not_before_time'), None)

                match emsevent['message']['name']:

                    case 'vsa.scheduledEvent.scheduled':
                        # found a new event

                        # did not find callhome.reboot.giveback for last az event
                        if azevent_dict['event_id'] != 'Unknown':
                            logging.error(f'Could not find completion for AZ event {azevent_dict["event_id"]}')
                            self.fetched_data['azmaints'][azevent_dict['event_id']] = azevent_dict
                            azevent_dict = {'event_id':'Unknown'}

                        # add the relevant bits from ems log event
                        azevent_dict['event_id'] = azevent_id
                        azevent_dict['node'] = node
                        azevent_dict['type'] = event_type
                        azevent_dict['timing']['az maint not before'] = datetime.strptime(not_before_time, '%m/%d/%Y %H:%M:%S').replace(tzinfo=timezone.utc)
                        azevent_dict['timing']['az maint scheduled'] = emsevent['time']

                    case 'vsa.scheduledEvent.update':
                        # will catch started and complete

                        # found an az ems event that is not the event that is being processed
                        if azevent_id != azevent_dict['event_id']:
                            logging.error(f"Found an out of order az event")
                            logging.error(f"Current Event: {azevent_dict['event_id']}")
                            logging.error(f"New Event ID: {azevent_id}")
                            logging.error(f"Full event details: {emsevent.to_dict()}")
                            if azevent_dict['event_id'] == 'Unknown':
                                azevent_dict['event_id'] = azevent_id
                                azevent_dict['node'] = node
                                azevent_dict['type'] = event_type
                        else:
                            azevent_dict['timing'][f"az maint {status}"] = emsevent['time']

                    case 'sfo.takenOver.relocDone':
                        # takeover complete
                        azevent_dict['timing']['node takeover complete'] = emsevent['time']

                    # case 'vifmgr.lifmoved.nodedown':
                    #     # takeover complete
                    #     if 'node takeover complete' not in azevent_dict['timing']:
                    #         azevent_dict['timing']['node takeover complete'] = emsevent['time']

                    case 'kern.shutdown':
                        # node starts rebooting
                        azevent_dict['timing']['node reboot starts'] = emsevent['time']

                    case 'mgr.boot.disk_done':
                        # node finished rebooting
                        azevent_dict['timing']['node reboot complete'] = emsevent['time']

                    case 'cf.fsm.takeoverOfPartnerEnabled':
                        # node ready for giveback
                        azevent_dict['timing']['node ready for giveback'] = emsevent['time']

                    case 'clam.valid.config':
                        # not failback starts
                        azevent_dict['timing']['node giveback starts'] = emsevent['time']

                    case 'callhome.reboot.giveback':
                        # the event is all done
                        # node failback is complete
                        azevent_dict['timing']['node giveback complete'] = emsevent['time']
                        azevent_id = azevent_dict['event_id']
                        if azevent_id == 'Unknown':
                            logging.error(f"No Event Id for {azevent_dict}")
                        else:
                            self.fetched_data['azmaints'][azevent_id] = azevent_dict
                            azevent_dict = self.empty_azevent()

            if azevent_dict['event_id'] != 'Unknown':
                logging.error(f"AZ event was left on stack")
                logging.error(f"{azevent_dict}")

        # pprint.pprint(self.fetched_data['azmaints'])

    def process_data(self):
        for event in self.fetched_data['azmaints'].values():
            required_timings = self.required_timings[:]
            print('------------------------------------------------')
            print(f"{'Event Id':<25} : {event['event_id']}")
            print(f"{'Node':<25} : {event['node']}")
            print(f"{'Type':<25} : {event['type']}")
            sorted_keys_by_time = sorted(event['timing'].items(), key=lambda item: item[1])

            for key, value in sorted_keys_by_time:
                required_timings.remove(key)
                print(f"{key:<25} : {value}")
            if required_timings:
                print(f"Times not found : {', '.join(required_timings)}")


if __name__ == '__main__':
    args = argp(description="check clusters for licensing issues")
    config = Config(args.data_dir)

    items = config.get_clusters(args.filter)

    APP = AppClass('check_license', items, config)
    APP.go()

