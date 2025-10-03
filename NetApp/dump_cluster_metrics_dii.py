import logging
import json
import pathlib
import pprint
import time
import datetime
import math
import collections
from zoneinfo import ZoneInfo

from netapp_ontap import HostConnection
from netapp_ontap.resources import Cluster, Volume, Node

from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger
from libs.openapi import APIWrapper
from libs.sqlite.metrics_db import MetricDB
import libs.dii

setup_logger()

script_name = pathlib.Path(__file__).stem

config = None

APP = None

class AppClass:
    def __init__(self, name, clusters, config):
        # start_time="2025-09-12T00:00:00Z",
        # end_time="2025-09-15T00:00:00Z"
        self.config = config        
        tdate: datetime.datetime = datetime.datetime.strptime(self.config.args.date, "%Y-%m-%d")
        tdate = tdate.replace(tzinfo=ZoneInfo("GMT"))
        dt_start_date = tdate - datetime.timedelta(days=1)
        dt_end_date = tdate + datetime.timedelta(days=2)
        self.start_time = f'{dt_start_date:%Y-%m-%d}T{dt_start_date:%H:%M:%S}Z'
        self.end_time = f'{dt_end_date:%Y-%m-%d}T{dt_end_date:%H:%M:%S}Z'
        logging.info(f"Start time: {self.start_time}")
        logging.info(f"End time: {self.end_time}")
        # print(clusters)
        self.name = name
        self.cluster_details = clusters
        self.clusterdata = {}
        self.dii_api_client = APIWrapper(
            api_spec_path=config.get_schema_location("dii") / "api.json",
            schema_path=config.get_schema_location("dii") / "schema.json",
            base_url=config.settings["settings"]["dii"]["base_url"],
            auth_token=config.settings["settings"]["dii"]["api_ro_token"]
        )

        self.build_app()

    def build_app(self):
        for item in self.cluster_details:
            self.clusterdata[item] = ClusterData(item, self, **self.cluster_details[item])

    def gather_data(self, vol_output_file=None):
        for cluster in self.clusterdata.values():
            cluster.gather_data()

class ClusterData:
    def __init__(self, clustername: str, app_instance: AppClass, **kwargs):
        self.name = clustername
        self.cluster_type = ''
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.app_instance = app_instance
        self.volume_metrics = {}
        self.metrics_db = MetricDB(self.app_instance.config, db_name=f"{self.name}_{self.app_instance.config.args.date}_metrics.db")
        self.metrics_to_get = ["read_ops", "write_ops", "read_throughput", "write_throughput", "read_latency", "write_latency"]

    def gather_data(self):
        logging.info(f'Gathering data for cluster {self.name}')
        try:
            with HostConnection(self.ip, username='cvomon', password=config.settings['users']['cvomon']['enc'], verify=False):
                volume_args = {}
                volume_args['is_svm_root'] = False
                volume_args['fields'] = '*'

                volumes = list(Volume.get_collection(**volume_args))
                
                for volume in volumes:
                    self.gather_data_for_volume(volume['name'], volume['svm']['name'])
        except Exception as e:
            logging.error(f"Exception checking cluster {self.name}", exc_info=e)


    def gather_data_for_volume(self, volume_name, vserver_name):
        logging.info(f'  Gathering data for {self.name}:{vserver_name}:{volume_name}')  
        bad_keys = []
        try:
            # Note : boolean operators must be CAPITAL LETTERS
            filter_expr=f'vserver_name = "{vserver_name}" AND volume_name = "{volume_name}"'

            results = libs.dii.lake.query.timeseries.post(
                self.app_instance.dii_api_client,
                category="netapp_ontap",
                measurement="workload_volume",
                metrics=self.metrics_to_get,
                filter_expr=filter_expr,
                interval="60s",
                # lookback_minutes=1440
                start_time=self.app_instance.start_time,
                end_time=self.app_instance.end_time
            )
            self.volume_metrics[volume_name] = collections.OrderedDict()
            current_metrics = self.volume_metrics[volume_name]
            first = True 
            for metric in results:
                # print(f"Len {metric} {len(results[metric])}")
                # print(f"Keys: {results[metric][0].keys()}")
                for data in results[metric][0]['timeseries']:
                    timestamp = data['time'] // 1000                    
                    # dt_object = datetime.datetime.fromtimestamp(timestamp, tz=ZoneInfo("GMT"))
                    # if first:
                        # logging.info(f"Converted timestamp {dt_object:%a %b %d %H:%M:%S %Z %Y}")
                        # logging.info(f"Data timestamp      {data['timeString']}")
                    if timestamp not in current_metrics:
                        if not first:
                            logging.info(f'Got a new timestamp for metric {metric} and time {data["time"]}')
                        current_metrics[timestamp] = {}
                        current_metrics[timestamp]['timestamp'] = timestamp

                    try:
                        current_metrics[timestamp][metric] = data['value']
                    except KeyError as e:
                        bad_keys.append(timestamp)
                        logging.debug(f"bad timestamp data: {volume_name} {metric} {data}")#, exc_info=e)

                first = False

            # clean up any bad data
            for item in bad_keys:
                if item in current_metrics and 'timestamp' in current_metrics[item] and len(current_metrics[item]) == 1:
                    del current_metrics[item]

            # look for data with missing data points
            number_of_metrics = len(self.metrics_to_get) + 1 # include timestamp key
            for item in current_metrics:
                if len(current_metrics[item]) != number_of_metrics:
                    logging.error(f"timestamp {item} does not have {number_of_metrics} keys")
                    logging.error(pprint.pformat(current_metrics[item]))

            # Add the data to database
            table_name = f"{vserver_name}-{volume_name}"
            self.metrics_db.create_table(table_name)
            metrics_list = list(current_metrics.values()) 
            self.metrics_db.upsert_many(table_name, metrics_list)

        except Exception as e:
            logging.error(f"Could not retrieve data for {self.name}:{vserver_name}:{volume_name}", exc_info=e)


if __name__ == "__main__":

    args = argp(script_name=script_name, description="dump volume metrics for a specific day (+/- done day for 3 days total)", parse=False)
    args.parser.add_argument('-d', '--date', type=str, help="the date of the form YYYY-MM-DD, example: 2025-04-13", default="", required=True)    
    args.parse()

    config = Config(args.config_dir, args.output_dir, args=args)

    items = config.get_clusters(args.filter)

    APP = AppClass('Provisioned', items, config)
    APP.gather_data()


    # print("-------------------- get_schema_for_endpoint -----------------------------")
    # pprint.pprint(client.get_schema_for_endpoint("/lake/query/timeseries", "post"))
    # print("--------------------------------------------------------------------------")
    # print("----------------------- suggest_paramters --------------------------------")
    # pprint.pprint(client.suggest_parameters("lake/query/timeseries", "post"))
    # print("--------------------------------------------------------------------------")
    #   "tagSet": {
    #     "cluster_name": "ZUSE2PDAXCST210",
    #     "workload_volume_name": "PD2TY2024_E2210-wid52741",
    #     "volume_name": "PD2TY2024_E2210",
    #     "vserver_name": "svm_ZUSE2PDAXCST210"
    #   },

    # metrics = ["read_ops", "write_ops", "read_throughput", "write_throughput", "read_latency", "write_latency"]
    # # metrics = ["performance.latency.read"]
    # results = libs.dii.lake.query.timeseries.post(
    #     client,
    #     category="netapp_ontap",
    #     measurement="workload_volume",
    #     # category="odata",
    #     # measurement="internalvolume",
    #     metrics=metrics,
    #     # Note : boolean operators must be CAPITAL LETTERS
    #     filter_expr='cluster_name = "ZUSE2PDAXCST210" AND vserver_name = "svm_ZUSE2PDAXCST210" AND volume_name = "PD2TY2024_E2210"',
    #     # filter_expr = 'volume_name CONTAINS "2024"', 
    #     # interval="60s",
    #     # lookback_minutes=1440
    #     start_time="2025-07-15T00:00:00Z",
    #     end_time="2025-07-30T00:00:00Z"
    # )

    # filename = config.output_dir / f"{script_name}.json"

    # with open(filename, "w") as f:
    #     json.dump(results, f, indent=2)

    # logging.info(f"Query completed. Results saved to {filename}")
