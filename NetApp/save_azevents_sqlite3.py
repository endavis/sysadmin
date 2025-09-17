"""

"""
from pathlib import Path
from datetime import datetime, timezone
import logging
import pprint
import traceback
import os

from netapp_ontap import HostConnection
from netapp_ontap.resources import EmsEvent, Node
import netapp_ontap.error

from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger
from libs.azevents_db import AzEventsDB
from libs.ems_db import EmsEventsDB

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
        self.cluster_data = {}
        self.dt_now = datetime.now()
        self.maint_db = AzEventsDB(config=self.config)

        self.build_app()

    def build_app(self):
        for item in self.cluster_details:
            self.cluster_data[item] = ClusterData(item, self, **self.cluster_details[item])

    def go(self):
        for cluster in self.cluster_data.values():
            try:
                cluster.gather_data()
                cluster.process_data()
            except netapp_ontap.error.NetAppRestError:
                logging.error(f"{cluster.name} : Could not connect to API")

        self.maint_db.conn.close()


class ClusterData:
    def __init__(self, clustername, app_instance, **kwargs):
        self.name = clustername
        self.cluster_type = ''
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.fetched_data = {}
        self.app_instance = app_instance
        self.invalid_maintenace = False
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
        self.current_azevent = ''
        return {'event_id':'Unknown'}

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

    def add_emsevent(self, emsevent):
        event_dict = {
            'event_id' : self.current_azevent,
            'cluster' : self.name,
            'node' : emsevent['node']['name'],
            'time' : emsevent['time'],
            'event' : emsevent['message']['name'],
            'severity' : emsevent['message']['severity'],
            'message' : emsevent['log_message'].replace(f"{emsevent['message']['name']}: ", "").replace(',', ';').replace('\n', '').strip()
        }
        self.fetched_data['ems_events'].append(event_dict)

    def add_azmaint(self, azmaint):
        if azmaint['event_id'] in self.fetched_data['azmaints']:
            self.fetched_data['azmaints'][azmaint['event_id']].update(azmaint)
        else:
            self.fetched_data['azmaints'][azmaint['event_id']] = azmaint
        self.current_azevent = ''

    def save_emsevents(self, db_name):
        if os.path.exists(db_name):
            logging.info(f"{db_name} already exists")
            return
        emsdb = EmsEventsDB(config=self.app_instance.config, db_name=db_name, overwrite=False)
        if not emsdb.exists:
            for emsevent in self.fetched_data['ems_events']:
                emsdb.insert_event(emsevent)
            emsdb.conn.close()
            logging.error(f"All events saved to {db_name}")
        else:
            logging.info(f"Events already saved to {db_name}")

    def gather_data(self):
        logging.info(f"{script_name} : Checking {self.name}")
        emsevent = None
        azevent_id = 'Unknown'
        try:
            self.fetched_data['azmaints'] = {}
            self.fetched_data['ems_events'] = []
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

                nodes = list(Node.get_collection(fields="ha"))
                if len(nodes) > 1 and nodes[0]['ha']['enabled']:
                    self.cluster_type = 'CVO HA'
                else:
                    self.cluster_type = 'CVO'

                events_to_get = ['vsa.scheduledEvent.scheduled', 'vsa.scheduledEvent.update']

                scheduled = list(EmsEvent.get_collection(**{"message.name": ",".join(events_to_get)}, order_by="time",fields="*"))

                if len(scheduled) == 0:
                    logging.info(f"{self.name} : No maintenance events")
                else:
                    logging.info(f"{self.name} : Found maintenance events")
                    for emsevent in EmsEvent.get_collection(**{"message.severity": "*"}, order_by="time",fields="*"):

                        #logging.debug(emsevent.to_dict())
                        self.add_emsevent(emsevent)

                        if 'vsa.scheduled' in emsevent['message']['name']:
                            logging.debug(f"Found vsa.scheduled {emsevent.to_dict()}")
                            azevent_id = next((item['value'] for item in emsevent['parameters'] if item['name'] == 'event_id'), None)
                            event_type = next((item['value'] for item in emsevent['parameters'] if item['name'] == 'event_type'), None)
                            node = next((item['value'] for item in emsevent['parameters'] if item['name'] == 'node'), None)
                            status = next((item['value'] for item in emsevent['parameters'] if  item['name'] == 'status'), None)
                            not_before_time = next((item['value'] for item in emsevent['parameters'] if item['name'] == 'not_before_time'), None)

                        match emsevent['message']['name']:

                            case 'vsa.scheduledEvent.scheduled':
                                logging.debug(f"Found vsa.scheduledEvent.scheduled for {emsevent.to_dict()}")
                                # found a new event
                                # did not find callhome.reboot.giveback for last az event
                                if azevent_dict['event_id'] != 'Unknown':
                                    logging.error(f'{self.name} Could not find completion for AZ event {azevent_dict["event_id"]}')
                                    self.add_azmaint(azevent_dict)
                                    azevent_dict = self.empty_azevent()

                                # add the relevant bits from ems log event
                                try:
                                    azevent_dict['az_maint_not_before'] = datetime.strptime(not_before_time, '%m/%d/%Y %H:%M:%S').replace(tzinfo=timezone.utc)
                                    azevent_dict['event_id'] = azevent_id
                                    azevent_dict['node'] = node
                                    azevent_dict['type'] = event_type
                                    azevent_dict['cluster'] = self.name
                                    azevent_dict['az_maint_scheduled'] = emsevent['time']

                                    self.current_azevent = azevent_id

                                except Exception as e:
                                    self.current_azevent = 'Unknown'
                                    logging.error(f"Got an invalid maintenance event {emsevent.to_dict()}")
                                    self.invalid_maintenace = True

                            case 'vsa.scheduledEvent.update':
                                logging.debug(f"Found vsa.scheduledEvent.update for {emsevent.to_dict()}")


                                # will catch started and complete

                                # found an az ems event that is not the event that is being processed
                                if azevent_id != azevent_dict['event_id']:
                                    logging.error(f"Found an out of order az event")
                                    logging.error(f"Current Event: {azevent_dict['event_id']}")
                                    logging.error(f"Current Event details: {azevent_dict}")
                                    logging.error(f"Full current EMS details: {emsevent.to_dict()}")
                                    self.add_azmaint(azevent_dict)
                                    self.empty_azevent()
                                    logging.error(f"New Event ID: {azevent_id}")
                                    if azevent_dict['event_id'] == 'Unknown':
                                        azevent_dict['event_id'] = azevent_id
                                        azevent_dict['node'] = node
                                        azevent_dict['type'] = event_type
                                else:
                                    azevent_dict[f"az_maint_{status}"] = emsevent['time']

                                if status == 'complete' and self.cluster_type == 'CVO':
                                    self.add_azmaint(azevent_dict)
                                    azevent_dict = self.empty_azevent()

                            case 'cf.fsm.nfo.startingGracefulShutdown':
                                # logging.debug(f"Found cf.fsm.nfo.startingGracefulShutdown for {azevent_id}")
                                # takeover complete
                                azevent_dict['node_takeover_complete'] = emsevent['time']

                            case 'kern.shutdown':
                                # logging.debug(f"Found kern.shutdown for {azevent_id}")
                                # node starts rebooting
                                azevent_dict['node_reboot_starts'] = emsevent['time']

                            case 'mgr.boot.disk_done':
                                # logging.debug(f"Found mgr.boot.disk_done for {azevent_id}")
                                # node finished rebooting
                                azevent_dict['node_reboot_complete'] = emsevent['time']

                            case 'cf.fsm.takeoverOfPartnerEnabled':
                                # logging.debug(f"Found cf.fsm.takeoverOfPartnerEnabledfor {azevent_id}")
                                # node ready for giveback
                                azevent_dict['node_ready_for_giveback'] = emsevent['time']

                            case 'clam.valid.config':
                                # logging.debug(f"Found clam.valid.config for {azevent_id}")
                                # not failback starts
                                azevent_dict['node_giveback_starts'] = emsevent['time']

                            case 'callhome.reboot.giveback':
                                # logging.debug(f"Found callhome.reboot.giveback for {azevent_id}")
                                # the event is all done
                                # node failback is complete
                                azevent_dict['node_giveback_complete'] = emsevent['time']
                                azevent_id = azevent_dict['event_id']
                                if azevent_id == 'Unknown':
                                    logging.error(f"{self.name} No Event Id for {azevent_dict}")
                                else:
                                    # add here since current_azevent is being reset
                                    self.add_emsevent(emsevent)
                                    self.add_azmaint(azevent_dict)
                                self.current_azevent = ''
                                azevent_dict = self.empty_azevent()

                    if azevent_dict['event_id'] != 'Unknown':
                        logging.error(f"AZ event was left on stack")
                        logging.error(f"{azevent_dict}")
                        self.add_azmaint(azevent_dict)

            # pprint.pprint(self.fetched_data['azmaints'])
        except Exception as e:
            logging.error(f"Could not retrieve events for {self.name} {e}")
            logging.error(traceback.format_exc(e))
            if emsevent:
                logging.error(f"last ems event was {emsevent}")

    def process_data(self):
        # if self.invalid_maintenace:
        #     db_name = f"{self.name}_invalidmaint_{self.app_instance.dt_now:%Y-%m-%d-%H-%M-%S}.db"
        #     self.save_emsevents(db_name)

        for azevent in self.fetched_data['azmaints'].values():
            logging.info(f"Cluster {self.name} adding {azevent['event_id']} for node {azevent['node']}")
            self.app_instance.maint_db.upsert_event(azevent)

            if azevent['event_id'] == 'Unknown':
                db_name = f"{self.name}_Unknown_{self.app_instance.dt_now:%d-%m-%Y-%H-%M-%S}.db"
                logging.error(f"Found an event without an id {azevent}")
                self.save_emsevents(db_name)
            else:
                azevent_from_db = dict(self.app_instance.maint_db.get_event_by_id(azevent['event_id']))

                if azevent_from_db['az_maint_not_before'] == "" \
                       or azevent_from_db['az_maint_scheduled'] == "" \
                       or azevent_from_db['az_maint_started'] == "" \
                       or azevent_from_db['az_maint_complete'] == "":
                    db_name = f"{self.name}_{azevent_from_db['event_id']}_nomaint_{self.app_instance.dt_now:%d-%m-%Y-%H-%M-%S}.db"
                    logging.error(f"Found an event without maintenance fields {azevent_from_db}")
                    self.save_emsevents(db_name)

                elif self.cluster_type == 'CVO HA' and any(value == "" for value in azevent_from_db.values()):
                    db_name = f"{self.name}_{azevent_from_db['event_id']}_CVOHAmissingfields_{self.app_instance.dt_now:%d-%m-%Y-%H-%M-%S}.db"
                    logging.error(f"Found a CVO HA maintenance event without failover/failback fields {azevent_from_db}")
                    self.save_emsevents(db_name)

if __name__ == '__main__':
    args = argp(script_name=script_name, description="save maintenance events to a sqlite db")
    config = Config(args.config_dir, args.output_dir)

    items = config.get_clusters(args.filter)

    APP = AppClass(script_name, items, config)
    APP.go()

