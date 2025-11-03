import base64
import logging
from libs.openapi import APIWrapper


class ONTAPAPIClient(APIWrapper):
    def __init__(self, cluster, config, **kwargs):
        self.cluster = cluster
        self.config = config

        user, enc = self.config.get_user("clusters", cluster.name)
        b64string = base64.b64encode(f"{user}:{enc}".encode("ascii"))
        auth_header = {"authorization": f"Basic {b64string.decode()}"}
        # logging.info(f"b64 password: {b64string.decode()}")

        super().__init__(
            api_json_file=config.get_schema_location("ontap") / "all.json",
            base_url=f"https://{cluster.ip}",
            auth_header=auth_header,
            base_api_path=self.config.settings["ontapapi"]["general"]["base_api_path"]
            ** kwargs,
        )
