"""validate ability to connect and that the config matches"""

# import logging
# import pprint
import traceback
import pathlib

from netapp_ontap import HostConnection
from netapp_ontap.resources import Cluster, Node, Volume

from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger

# logging.basicConfig(level=logging.DEBUG)
# utils.LOG_ALL_API_CALLS = 1

script_name = pathlib.Path(__file__).stem

setup_logger(script_name)

config = None

APP = None


class AppClass:
    def __init__(self, name, clusters, config):
        self.name = name
        self.cluster_details = clusters
        self.clusterdata = {}
        self.build_app()
        self.config = config
        self.count = {}
        self.count["nodes"] = 0
        self.count["volumes"] = 0

    def build_app(self):
        for item in self.cluster_details:
            self.clusterdata[item] = ClusterData(
                item, self, **self.cluster_details[item]
            )

    def gather_data(self, vol_output_file=None):
        for cluster in self.clusterdata.values():
            cluster.gather_data()
            self.count["nodes"] += cluster.count["nodes"]
            self.count["volumes"] += cluster.count["volumes"]

        print(f"# of nodes: {self.count['nodes']}")
        print(f"# of volumes: {self.count['volumes']}")


class ClusterData:
    def __init__(self, clustername, app_instance, **kwargs):
        self.name = clustername
        self.app_instance = app_instance
        self.cluster_type = ""
        self.count = {}
        for name, value in kwargs.items():
            setattr(self, name, value)

    def gather_data(self):
        user, enc = self.app_instance.config.get_user("clusters", self.name)
        try:
            with HostConnection(self.ip, username=user, password=enc, verify=False):
                cluster = Cluster()

                cluster.get()

                nodes = Node()
                tnodes = nodes.get_collection()
                self.count["nodes"] = len(list(tnodes))

                volumes = Volume()
                tvolumes = volumes.get_collection()
                self.count["volumes"] = len(list(tvolumes))

                print(f"Config {self.name} connected successfully")

                if cluster["name"] != self.name:
                    print(
                        f'    Config name {self.name} does not match cluster name {cluster["name"]}'
                    )
        except:
            print(f"Could not connect to config {self.name}")
            print(traceback.format_exc())


if __name__ == "__main__":
    args = argp(
        script_name=script_name,
        description="check connection and that cluster names match",
    )
    config = Config(args.config_dir, args.output_dir)

    items = config.get_clusters(args.filter)
    # pprint.pprint(items)

    APP = AppClass(script_name, items, config)
    APP.gather_data()
