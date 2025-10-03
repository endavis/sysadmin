# dii
from pathlib import Path
from libs.import_utils import import_all_files

package_name = __name__
package_path = Path(__file__).parent

import_all_files(package_name=package_name, package_path=package_path)

