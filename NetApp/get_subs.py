"""cluster1::> set -showallfields true

cluster1::> set -showseparator ","
"""

import pathlib
import logging
import pprint


from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger
from libs.ontap.cli import ONTAPCLI

script_name = pathlib.Path(__file__).stem

setup_logger(script_name)


config = None

APP = None


class AppClass:
    def __init__(self, name, clusters, config):
        # print(clusters)
        self.config = config
        self.name = name
        self.cluster_details = clusters
        self.cluster_data = {}
        self.output = []
        self.output.append("Node,Time,Event,Severity,Message")
        self.data = {}

        self.build_app()

    def build_app(self):
        for item in self.cluster_details:
            self.cluster_data[item] = ClusterData(
                item, self, **self.cluster_details[item]
            )

    def go(self):
        for cluster in self.cluster_data.values():
            cluster.gather_data()
            if not self.data:
                self.data = cluster.subs.copy()
            else:
                for sub in cluster.subs:
                    print(f"Adding {sub} for {cluster.name}")
                    self.data[sub] = list(set(self.data[sub]) & set(cluster.subs[sub]))
            # cluster.process_data()

        pprint.pprint(self.data)


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

        self.subs = {}

    def gather_data(self):
        # self.cli.connect()
        # results = self.ssh.run_command_and_parse("system node virtual-machine instance show")
        # results = self.ssh.run_command_and_parse("volume show", "-instance T4TY202*")
        # results = self.ssh.run_command_and_parse("storage aggregate show -instance")
        # try:
        #     results = self.cli.run_command("rows 0;vol show T4TY2022 -fields tiering-policy,tiering-minimum-cooling-days")
        #     pprint.pprint(results)
        # except Exception as e:
        #     logging.error("Error during command", exc_info=e)

        # try:
        #     results = self.cli.run_command("rows 0;set d -confirmations off;vol show T4TY2022 -fields tiering-policy,tiering-minimum-cooling-days")
        #     pprint.pprint(results)
        # except Exception as e:
        #     logging.error("Error during command", exc_info=e)

        # try:
        #     data, descriptions = self.cli.run_a_show_command_and_parse_seperator('vol show', '-volume T4TY2022')
        #     pprint.pprint(descriptions)
        #     pprint.pprint(data)
        # except Exception as e:
        #     logging.error("Error during command", exc_info=e)

        # try:
        #     output = self.cli.run_command('system node virtual-machine instance show')
        #     pprint.pprint(output)
        # except Exception as e:
        #     logging.error("Error during command", exc_info=e)

        try:
            data, descriptions = self.cli.run_a_show_command_and_parse_seperator(
                "system node virtual-machine instance show"
            )
            for item in data:
                if item["provider"] == "Azure":
                    account_id = item["account-id"]
                    if account_id not in self.subs:
                        self.subs[account_id] = []
                    if item["resource-group-name"] not in self.subs[account_id]:
                        self.subs[account_id].append(item["resource-group-name"])

            # if data['']
            # pprint.pprint(data)
            # pprint.pprint(descriptions)
        except Exception as e:
            logging.error("Error during command", exc_info=e)

        # try:
        #     self.cli.run_command_api('vserver services web show', privilege_level='diagnostic', vserver='svm_ZUSCUNPAXCST004')
        # except Exception as e:
        #     logging.error("Error during command", exc_info=e)

        # try:
        #     self.cli.run_command_python_api(
        #         "system node virtual-machine instance show",
        #         privilege_level="diagnostic",
        #         fields="account-id,instance-id,provider",
        #     )
        # except Exception as e:
        #     logging.error("Error during command", exc_info=e)

    def process_data(self): ...


if __name__ == "__main__":
    args = argp(script_name=script_name, description="test cli")
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
