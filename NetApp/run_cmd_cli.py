""" """

import pathlib
import logging

from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger
from libs.ontap.cli import ONTAPCLI

script_name = pathlib.Path(__file__).stem

setup_logger(script_name)


class AppClass:
    def __init__(self, name, clusters, config):
        self.config = config
        self.name = name
        self.cluster_details = clusters
        self.cluster_data = {}
        self.output = []
        self.output.append("Node,Time,Event,Severity,Message")

        self.build_app()

    def build_app(self):
        for item in self.cluster_details:
            self.cluster_data[item] = ClusterData(
                item, self, **self.cluster_details[item]
            )

    def go(self):
        for cluster in self.cluster_data.values():
            cluster.gather_data()


class ClusterData:
    def __init__(self, clustername, app_instance, **kwargs):
        self.name = clustername
        self.cluster_type = ""
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.fetched_data = {}
        self.app_instance = app_instance
        self.creds = {}

        user, enc = self.app_instance.config.get_user("clusters", self.name)
        self.creds["user"] = user
        self.creds["enc"] = enc

        self.cli = ONTAPCLI(
            self.name,
            self.ip,  # pyright: ignore[reportAttributeAccessIssue]
            self.creds["user"],
            self.creds["enc"],
        )

    def gather_data(self):

        try:
            output = self.cli.run_command(self.app_instance.config.args.cmd)
        except Exception as e:
            logging.error("Error during command", exc_info=e)


if __name__ == "__main__":
    args = argp(script_name=script_name, description="test cli", parse=False)
    args.parser.add_argument(
        "--cmd", type=str, help="the command to run", default="", required=True
    )
    args.parse()

    config = Config(
        args.config_dir,  # pyright: ignore[reportAttributeAccessIssue]
        args.output_dir,  # pyright: ignore[reportAttributeAccessIssue]
        script_name=script_name,
        args=args,
    )
    items = config.get_clusters(
        args.filter  # pyright: ignore[reportAttributeAccessIssue]
    )

    APP = AppClass(script_name, items, config)
    APP.go()
