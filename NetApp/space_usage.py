"""
This goes through all volumes and puts the data in 1 of 4 buckets

CVO HA, RW volume
CVO HA, DP volume
CVO, RW volume
CVO, DP volume
"""

import logging
import pprint
import traceback
from datetime import datetime

from netapp_ontap import HostConnection
from netapp_ontap.resources import Cluster, Volume
import xlsxwriter


from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger
from libs.size_utils import approximate_size_specific

setup_logger()

#logging.basicConfig(level=logging.DEBUG)
#utils.LOG_ALL_API_CALLS = 1
#=SUMIFS(Volumes!$L$2:$L$478,Volumes!$B$2:$B$478,"MRFS")

config = None

APP = None

class AppClass:
    def __init__(self, name, clusters):
        self.name = name
        self.cluster_details = clusters
        self.clusterdata = {} 
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")            
        self.filename = config.output_dir / f"space_usage_{timestamp}.xlsx"              

        self.workbook = xlsxwriter.Workbook(self.filename)
        self.usage_ws = self.workbook.add_worksheet("Usage")
        self.volumes_ws = self.workbook.add_worksheet("Volumes")
        self.volume_data = []

        # Define common format with Cascadia Mono font size 10
        self.cell_format = self.workbook.add_format({'font_name': 'Cascadia Mono', 'font_size': 10})
        self.cell_format_number = self.workbook.add_format({'font_name': 'Cascadia Mono', 'font_size': 10, })
        self.cell_format_number.set_num_format('0.000')
        self.cell_format_red = self.workbook.add_format({'font_name': 'Cascadia Mono', 'font_size': 10})
        self.cell_format_red.set_bg_color("red")
        self.cell_format_red.set_font_color("white")

        self.divisions = {}
        self.build_app()

    def build_app(self):
        for item in self.cluster_details:
            div = self.cluster_details[item]['div']
            bu = self.cluster_details[item]['bu']
            app = self.cluster_details[item]['app']
            env = self.cluster_details[item]['env']
            subapp = self.cluster_details[item]['subapp']
            cloud = self.cluster_details[item]['cloud']
            region = self.cluster_details[item]['region']
            if div not in self.divisions:
                self.divisions[div] = {}
            if bu not in self.divisions[div]:
                self.divisions[div][bu] = {}
            if app not in self.divisions[div][bu]:
                self.divisions[div][bu][app] = {}
            if env not in self.divisions[div][bu][app]:
                self.divisions[div][bu][app][env] = {}
            if subapp not in self.divisions[div][bu][app][env]:
                self.divisions[div][bu][app][env][subapp] = {}
            if cloud not in self.divisions[div][bu][app][env][subapp]:
                self.divisions[div][bu][app][env][subapp][cloud] = []
            if region not in self.divisions[div][bu][app][env][subapp][cloud]:
                self.divisions[div][bu][app][env][subapp][cloud].append(region)

            self.clusterdata[item] = ClusterData(item, self, **self.cluster_details[item])

    def go(self):
        for cluster in self.clusterdata.values():
            cluster.gather_data()

        self.build_volume_sheet()
        self.build_usage_sheet()
        
        self.workbook.close()
        logging.info(f"Data saved to {self.filename}")       

    def build_volume_sheet(self):
        
        # Headers for Volumes sheet
        volumes_headers = [
            "Division", "BU", "Cluster", "App", "Environment", "SubApp", "Cloud",
            "Region", "Volume", "State", "Tags", "Provisioned Size [TiB]", "Used Size TiB", "%% used"
        ]
        number_format = ["Provisioned Size [TiB]", "Used Size TiB", "%% used"]
        # Write headers to Volumes sheet
        for col_num, header in enumerate(volumes_headers):
            self.volumes_ws.write(0, col_num, header, self.cell_format)

        # Write data and track max column width
        volumes_col_widths = [len(header) + 1 for header in volumes_headers]
        for row_num, row_data in enumerate(self.volume_data, start=1):
            for col_num, cell in enumerate(row_data):
                cell_format = self.cell_format
                if volumes_headers[col_num] in number_format:
                    cell_format = self.cell_format_number
                self.volumes_ws.write(row_num, col_num, cell, cell_format)
                cell_length = len(str(cell))
                if cell_length > volumes_col_widths[col_num]:
                    volumes_col_widths[col_num] = cell_length

        # Apply autofilter to Volumes sheet
        self.volumes_ws.autofilter(0, 0, len(self.volume_data), len(volumes_headers) - 1)

        # Auto-size columns for Volumes sheet
        for col_num, width in enumerate(volumes_col_widths):
            self.volumes_ws.set_column(col_num, col_num, width + 4)

        # self.volumes_ws.autofit()
        self.volumes_ws.conditional_format(f"N2:N{len(self.volume_data) + 1}", {"type": "cell", "criteria": ">=", "value": 90, "format": self.cell_format_red})


    def build_usage_sheet(self):
        provision_col_header = "Provisioned TiB"
        used_col_header = "Used TiB"
        usage_headers = ["Division", "BU", "App", "Environment", "SubApp", "Cloud", "Region", provision_col_header, used_col_header, '%% Used']
        numbers_format = [provision_col_header, used_col_header, '%% Used']

        volume_last_row = len(self.volume_data) + 1
        usage_data = []


        # Write headers to Usage sheet
        for col_num, header in enumerate(usage_headers):
            self.usage_ws.write(0, col_num, header, self.cell_format)
      
        # get the totals
        for div in self.divisions:
            for bu in self.divisions[div]:
                for app in self.divisions[div][bu]:
                    for env in self.divisions[div][bu][app]:
                        for subapp in self.divisions[div][bu][app][env]:
                            for cloud in self.divisions[div][bu][app][env][subapp]:
                                for region in self.divisions[div][bu][app][env][subapp][cloud]:
                                    usage_data.append([div, bu, app, env, subapp, cloud, region, 
                                                        f'=SUMIFS(Volumes!$L$2:$L${volume_last_row},Volumes!$A$2:$A${volume_last_row},"{div}",Volumes!$B$2:$B${volume_last_row},"{bu}",Volumes!$D$2:$D${volume_last_row},"{app}",Volumes!$E$2:$E${volume_last_row},"{env}",Volumes!$F$2:$F${volume_last_row},"{subapp}",Volumes!$G$2:$G${volume_last_row},"{cloud}",Volumes!$H$2:$H${volume_last_row},"{region}")',
                                                        f'=SUMIFS(Volumes!$M$2:$M${volume_last_row},Volumes!$A$2:$A${volume_last_row},"{div}",Volumes!$B$2:$B${volume_last_row},"{bu}",Volumes!$D$2:$D${volume_last_row},"{app}",Volumes!$E$2:$E${volume_last_row},"{env}",Volumes!$F$2:$F${volume_last_row},"{subapp}",Volumes!$G$2:$G${volume_last_row},"{cloud}",Volumes!$H$2:$H${volume_last_row},"{region}")',
                                                        ""])


        # Write data and track max column width
        usage_col_widths = [len(header) + 1 for header in usage_headers]
        for row_num, row_data in enumerate(usage_data, start=1):
            for col_num, cell in enumerate(row_data):
                cell_format = self.cell_format
                if usage_headers[col_num] in numbers_format:
                    cell_format = self.cell_format_number
                self.usage_ws.write(row_num, col_num, cell, cell_format)
                cell_length = len(str(cell))
                if (not str(cell).startswith('=')) and cell_length > usage_col_widths[col_num]:
                    usage_col_widths[col_num] = cell_length
            
        
        formula = f"=[@[{used_col_header}]]/[@[{provision_col_header}]] * 100"

        # Add table with style and total row
        table_range = f"A1:J{len(usage_data)+2}"
        self.usage_ws.add_table(table_range, {

        'columns': [
            {'header': "Division", 'total_string': ''},
            {'header': "BU", 'total_string': ''},
            {'header': "App", 'total_string': ''},
            {'header': "Environment", 'total_string': ''},
            {'header': "SubApp", 'total_string': ''},
            {'header': "Cloud", 'total_string': ''},
            {'header': "Region", 'total_string': ''},
            {'header': provision_col_header, 'total_function': 'sum'},
            {'header': used_col_header, 'total_function': 'sum'},
            {'header': "% Used", 'formula': formula, 'total_function': 'average', 'format':self.cell_format_number}],

            'style': 'Table Style Medium 9',
            'autofilter': True,
            'total_row': True,
            'name':'usage_table'
        })

        # Auto-size columns for Usage sheet
        for col_num, width in enumerate(usage_col_widths):
            self.usage_ws.set_column(col_num, col_num, width + 2)

        self.usage_ws.conditional_format(f"J2:N{len(usage_data) + 2}", {"type": "cell", "criteria": ">=", "value": 90, "format": self.cell_format_red})


class ClusterData:
    def __init__(self, clustername: str, app_instance: AppClass, **kwargs):
        self.name = clustername
        self.cluster_type = ''
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.app_instance = app_instance

    def gather_data(self):
        logging.info(f'Gathering data for {self.name}')
        try:
            with HostConnection(self.ip, username='cvomon', password=config.settings['users']['cvomon']['enc'], verify=False):
                cluster = Cluster()

                cluster.get()
                volume_args = {}
                volume_args['is_svm_root'] = False
                volume_args['fields'] = '*'
                                        
                volumes = list(Volume.get_collection(**volume_args))
                for volume in volumes:
                    size = float(f"{approximate_size_specific(volume['size'], 'TiB', withsuffix=False):.7f}")
                    if volume['state'] == 'offline':
                        used = 0
                    else:
                        used = float(f"{approximate_size_specific(volume['space']['used'], 'TiB', withsuffix=False):.7f}")
                    self.app_instance.volume_data.append([self.div,
                                                 self.bu,
                                                 self.name,
                                                 self.app,
                                                 self.env,
                                                 self.subapp,
                                                 self.cloud,
                                                 self.region,
                                                 volume['name'],
                                                 volume['state'],
                                                 ",".join(self.tags),
                                                 size,
                                                 used,
                                                 float(f"{(used / size) * 100:.3f}")])
                    
        except Exception as e:
            logging.error(f"Could not retrieve data for {self.name} {volume['name']} {e}", exc_info=e)


if __name__ == '__main__':
    args = argp(description="gather volume and cluster stats, provisioned size and savings if changing to 80% and 90% autosize thresholds")
    config = Config(args.config_dir)

    items = config.get_clusters(args.filter)    

    APP = AppClass('Provisioned', items)
    APP.go()

