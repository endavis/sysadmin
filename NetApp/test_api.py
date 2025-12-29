""" """

import logging
import pathlib
import pprint

# from workbook import SpaceWorkbook

from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger
from libs.dii.api import DIIAPIClient
from libs.ontap.api import ONTAPAPIClient


script_name = pathlib.Path(__file__).stem

setup_logger(script_name)

APP = None


class AppClass:
    def __init__(self, name, clusters, config):
        self.config = config
        self.name = name
        self.cluster_details = clusters
        self.clusterdata = {}
        self.build_app()

    def build_app(self):
        for item in self.cluster_details:
            self.clusterdata[item] = ClusterData(
                item, self, **self.cluster_details[item]
            )

    def go(self):
        if self.config.args.api == "dii":
            # endpoint = "/assets/storages"
            endpoint = "/lake/query/object"
            method = "POST"
            client = DIIAPIClient(self.config)

            print(f"--------------- {endpoint} SCHEMA ---------------")
            pprint.pprint(
                client.get_request_schema_for_endpoint(endpoint, method)
                or f"No request schema for {endpoint}:{method}"
            )
            print("--------------- /api/cluster PARAMETERS ---------------")
            pprint.pprint(client.suggest_parameters(endpoint))
            print("--------------- END INFO ---------------")
            # try:
            #     response = client.call_endpoint(
            #         endpoint, method="GET", query_params={"limit": 1}
            #     )
            #     if not response:
            #         logging.debug(f"no data for {endpoint}")
            #     # pprint.pprint(response)
            # except Exception as e:
            #     logging.error(f"Error querying metric {endpoint}: {e}", exc_info=e)

        elif self.config.args.api == "ontap":
            for cluster in self.clusterdata.values():
                cluster.gather_data()


class ClusterData:
    def __init__(self, clustername: str, app_instance: AppClass, **kwargs):
        self.name = clustername
        self.cluster_type = ""
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.fetched_data = {}
        self.app_instance = app_instance

    def gather_data(self):
        logging.info(f"Gathering data for {self.name}")
        endpoint = "cluster"  # don't need api base, just the api
        client = ONTAPAPIClient(self, self.app_instance.config)
        # print("--------------- ENDPOINTS ---------------")
        # pprint.pprint(client.list_endpoints())
        # print("--------------- /api/cluster SCHEMA ---------------")
        # pprint.pprint(client.get_schema_for_endpoint(endpoint))
        # print("--------------- /api/cluster PARAMETERS ---------------")
        # pprint.pprint(client.suggest_parameters(endpoint))
        # print("--------------- END INFO ---------------")

        try:
            response = client.call_endpoint(
                endpoint,
                method="GET",
            )
            if not response:
                logging.debug(f"no data for {endpoint}")
            # pprint.pprint(response)
        except Exception as e:
            logging.error(f"Error querying metric {endpoint}: {e}", exc_info=e)


if __name__ == "__main__":
    args = argp(script_name=script_name, description="test dii", parse=False)
    args.parser.add_argument(
        "-a",
        "--api",
        type=str,
        help="the api (dii or ontap)",
        default="ontap",
        required=True,
    )
    args.parser.add_argument(
        "-e",
        "--endpoint",
        type=str,
        help="the api endpoint",
        default="",
        required=False,
    )
    args.parse()

    config = Config(
        args.config_dir,  # pyright: ignore[reportAttributeAccessIssue]
        args.output_dir,  # pyright: ignore[reportAttributeAccessIssue]
        args=args,
    )

    items = config.get_clusters(
        args.filter  # pyright: ignore[reportAttributeAccessIssue]
    )

    APP = AppClass(script_name, items, config)
    APP.go()
