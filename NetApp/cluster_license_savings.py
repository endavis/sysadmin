"""This goes through all volumes and puts the data in 1 of 4 buckets

CVO HA, RW volume
CVO HA, DP volume
CVO, RW volume
CVO, DP volume
"""

import logging
import traceback
import pathlib

# from workbook import SpaceWorkbook
from netapp_ontap import HostConnection  # pyright: ignore[reportPrivateImportUsage]
from netapp_ontap.resources import Cluster, Volume, Node

from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger
from libs.size_utils import approximate_size_specific

script_name = pathlib.Path(__file__).stem

setup_logger(script_name)

# logging.basicConfig(level=logging.DEBUG)
# utils.LOG_ALL_API_CALLS = 1

config = None

APP = None


class AppClass:
    def __init__(self, name, clusters, config):
        self.name = name
        self.config = config
        self.cluster_details = clusters
        self.clusterdata = {}
        self.build_app()
        self.vol_output_file = open(self.config.output_dir / "vol-out.csv", "w")
        self.vol_output_file.write(
            ",".join(
                [
                    "Cluster",
                    "Division",
                    "Business Unit",
                    "Bucket",
                    "App",
                    "Environment",
                    "Cloud Provider",
                    "Tags",
                    "Volume",
                    "Type",
                    "Size (TiB)",
                    "Used (TiB)",
                    "Percent Used",
                    "Size if volume was 80% used (TiB)",
                    "Savings (TiB)",
                    "\n",
                ]
            )
        )
        self.clus_output_file = open(self.config.output_dir / "cluster-out.csv", "w")
        self.clus_output_file.write(
            ",".join(
                [
                    "Cluster",
                    "Division",
                    "Business Unit",
                    "App",
                    "Environment",
                    "Cloud Provider",
                    "Tags",
                    "CVO - RW Provisioned Size (TiB)",
                    "CVO - RW Potential Savings (TiB)",
                    "CVO - RW Provisioned Size - Potential Savings",
                    "CVO - DP Provisioned Size (TiB)",
                    "CVO - DP Potential Savings (TiB)",
                    "CVO - DP Provisioned Size - Potential Savings",
                    "CVO HA - RW Provisioned Size (TiB)",
                    "CVO HA - RW Potential Savings (TiB)",
                    "CVO HA - RW Provisioned Size - Potential Savings",
                    "CVO HA - DP Provisioned Size (TiB)",
                    "CVO HA - DP Potential Savings (TiB)",
                    "CVO HA - DP Provisioned Size - Potential Savings",
                    "\n",
                ]
            )
        )

    def build_app(self):
        for item in self.cluster_details:
            self.clusterdata[item] = ClusterData(
                item, self, **self.cluster_details[item]
            )

    def gather_data(self, vol_output_file=None):
        for cluster in self.clusterdata.values():
            cluster.gather_data()

        logging.info(f"Volume output: {self.config.output_dir / 'vol-out.csv'}")
        logging.info(f"Cluster output: {self.config.output_dir / 'cluster-out.csv'}")


class ClusterData:
    def __init__(self, clustername, app_instance, **kwargs):
        self.name = clustername
        self.app_instance = app_instance
        self.cluster_type = ""
        for name, value in kwargs.items():
            setattr(self, name, value)

    def gather_data(self):
        logging.info(f"Gathering data for {self.name}")
        user, enc = self.app_instance.config.get_user("clusters", self.name)
        try:
            with HostConnection(
                self.ip,  # pyright: ignore[reportAttributeAccessIssue]
                username=user,
                password=enc,
                verify=False,
            ):
                cluster = Cluster()

                cluster.get()

                nodes = list(Node.get_collection(fields="ha"))
                if len(nodes) > 1 and nodes[0]["ha"]["enabled"]:
                    self.cluster_type = "CVO HA"
                else:
                    self.cluster_type = "CVO"

                buckets = {
                    "CVO HA - DP": {"provisioned_size": 0, "potential_savings": 0},
                    "CVO HA - RW": {"provisioned_size": 0, "potential_savings": 0},
                    "CVO - DP": {"provisioned_size": 0, "potential_savings": 0},
                    "CVO - RW": {"provisioned_size": 0, "potential_savings": 0},
                }

                args = {}
                args["is_svm_root"] = False
                args["fields"] = ",".join(
                    [
                        "name",
                        "size",
                        "aggregates",
                        "space",
                        "autosize.*",
                        "guarantee",
                        "space.*",
                        "type",
                    ]
                )

                volumes = list(Volume.get_collection(**args))
                for volume in volumes:
                    bucket = self.cluster_type + " - " + volume["type"].upper()
                    size_set_as_80 = 0
                    savings = 0
                    try:
                        if (
                            volume["space"]["percent_used"] < 80
                            and volume["size"] > 1073741824
                        ):
                            size_set_as_80 = volume["space"]["used"] * 1.2
                            savings = volume["size"] - size_set_as_80
                        else:
                            size_set_as_80 = volume["size"]
                    except:
                        logging.error(
                            f'Error getting info for volume {volume["name"]}'
                            f" in cluster {self.name}"
                        )
                        logging.error(traceback.format_exc())
                        continue
                    self.app_instance.vol_output_file.write(
                        ",".join(
                            [
                                self.name,
                                self.div,  # pyright: ignore[reportAttributeAccessIssue]
                                self.bu,  # pyright: ignore[reportAttributeAccessIssue]
                                bucket,
                                self.app,  # pyright: ignore[reportAttributeAccessIssue]
                                self.env,  # pyright: ignore[reportAttributeAccessIssue]
                                self.cloud,  # pyright: ignore[reportAttributeAccessIssue]
                                ";".join(
                                    self.tags  # pyright: ignore[reportAttributeAccessIssue]
                                ),
                                volume["name"],
                                volume["type"].upper(),
                                f"{approximate_size_specific(volume['size'], 'TiB', withsuffix=False)}",
                                f"{approximate_size_specific(volume['space']['used'], 'TiB', withsuffix=False)}",
                                f"{volume['space']['percent_used']}",
                                f"{approximate_size_specific(size_set_as_80, 'TiB', withsuffix=False)}",
                                f"{approximate_size_specific(savings, 'TiB', withsuffix=False)}",
                                "\n",
                            ]
                        )
                    )
                    buckets[bucket]["provisioned_size"] += volume["size"]
                    buckets[bucket]["potential_savings"] += savings

                self.app_instance.clus_output_file.write(
                    ",".join(
                        [
                            self.name,
                            self.div,  # pyright: ignore[reportAttributeAccessIssue]
                            self.bu,  # pyright: ignore[reportAttributeAccessIssue]
                            self.app,  # pyright: ignore[reportAttributeAccessIssue]
                            self.env,  # pyright: ignore[reportAttributeAccessIssue]
                            self.cloud,  # pyright: ignore[reportAttributeAccessIssue]
                            ";".join(
                                self.tags  # pyright: ignore[reportAttributeAccessIssue]
                            ),
                            f"{approximate_size_specific(buckets['CVO - RW']['provisioned_size'], 'TiB', withsuffix=False)}",
                            f"{approximate_size_specific(buckets['CVO - RW']['potential_savings'], 'TiB', withsuffix=False)}",
                            f"{approximate_size_specific(buckets['CVO - RW']['provisioned_size'] - buckets['CVO - RW']['potential_savings'], 'TiB', withsuffix=False)}",
                            f"{approximate_size_specific(buckets['CVO - DP']['provisioned_size'], 'TiB', withsuffix=False)}",
                            f"{approximate_size_specific(buckets['CVO - DP']['potential_savings'], 'TiB', withsuffix=False)}",
                            f"{approximate_size_specific(buckets['CVO - DP']['provisioned_size'] - buckets['CVO - DP']['potential_savings'], 'TiB', withsuffix=False)}",
                            f"{approximate_size_specific(buckets['CVO HA - RW']['provisioned_size'], 'TiB', withsuffix=False)}",
                            f"{approximate_size_specific(buckets['CVO HA - RW']['potential_savings'], 'TiB', withsuffix=False)}",
                            f"{approximate_size_specific(buckets['CVO HA - RW']['provisioned_size'] - buckets['CVO HA - RW']['potential_savings'], 'TiB', withsuffix=False)}",
                            f"{approximate_size_specific(buckets['CVO HA - DP']['provisioned_size'], 'TiB', withsuffix=False)}",
                            f"{approximate_size_specific(buckets['CVO HA - DP']['potential_savings'], 'TiB', withsuffix=False)}",
                            f"{approximate_size_specific(buckets['CVO HA - DP']['provisioned_size'] - buckets['CVO HA - DP']['potential_savings'], 'TiB', withsuffix=False)}",
                            "\n",
                        ]
                    )
                )
        except Exception as e:
            logging.error(f"Could not retrieve data for {self.name} {e}")


if __name__ == "__main__":
    args = argp(
        script_name=script_name,
        description="gather volume and cluster stats, provisioned"
        " size and savings if changing to 80% and 90% autosize thresholds",
    )
    config = Config(
        args.config_dir,  # pyright: ignore[reportAttributeAccessIssue]
        args.output_dir,  # pyright: ignore[reportAttributeAccessIssue]
        script_name=script_name,
        args=args,
    )

    items = config.get_clusters(
        args.filter  # pyright: ignore[reportAttributeAccessIssue]
    )

    APP = AppClass("Provisioned", items, config)
    APP.gather_data()
