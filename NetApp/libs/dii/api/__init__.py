# dii
from pathlib import Path

from libs.import_utils import import_all_files
from libs.openapi import APIWrapper

package_name = __name__
package_path = Path(__file__).parent

import_all_files(package_name=package_name, package_path=package_path)


class DIIAPIClient(APIWrapper):
    def __init__(self, config, **kwargs):
        self.config = config

        super().__init__(
            api_json_file=config.get_schema_location("dii") / "all.json",
            base_url=config.settings["diiapi"]["general"]["base_url"],
            auth_header={
                "X-CloudInsights-ApiKey": self.config.settings["diiapi"]["general"][
                    "api_ro_token"
                ]
            },
            base_api_path=self.config.settings["diiapi"]["general"]["base_api_path"],
            **kwargs,
        )
