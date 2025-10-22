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
import pathlib
from datetime import datetime

from netapp_ontap import HostConnection
from netapp_ontap.resources import Cluster, Volume, Node
import xlsxwriter
import xlsxwriter.utility

from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger
from libs.size_utils import approximate_size_specific

setup_logger()

script_name = pathlib.Path(__file__).stem

#logging.basicConfig(level=logging.DEBUG)
#utils.LOG_ALL_API_CALLS = 1
#=SUMIFS(Volumes!$L$2:$L$478,Volumes!$B$2:$B$478,"MRFS")

config = None

APP = None

class AppClass:
    def __init__(self, name, clusters, config):
        self.name = name
        self.config = config
        self.cluster_details = clusters
        self.clusterdata = {}
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.filename = self.config.output_dir / f"{script_name}_{timestamp}.xlsx"

        self.workbook = xlsxwriter.Workbook(self.filename)
        self.totals_ws = self.workbook.add_worksheet("Totals")
        self.usage_ws = self.workbook.add_worksheet("Usage Breakdown")
        self.volumes_ws = self.workbook.add_worksheet("Volumes")
        self.volume_data = []

        # Define common format with Cascadia Mono font size 10
        self.cell_format = self.workbook.add_format({'font_name': 'Cascadia Mono', 'font_size': 10})
        self.cell_format_number = self.workbook.add_format({'font_name': 'Cascadia Mono', 'font_size': 10, })
        self.cell_format_number.set_num_format('0.00000')
        self.cell_format_red = self.workbook.add_format({'font_name': 'Cascadia Mono', 'font_size': 10})
        self.cell_format_red.set_bg_color("red")
        self.cell_format_red.set_font_color("white")
        self.cell_format_percentage = self.workbook.add_format({'font_name': 'Cascadia Mono', 'font_size': 10})
        self.cell_format_percentage.set_num_format('0.00%')

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
                self.divisions[div][bu][app][env][subapp][cloud] = {}
            if region not in self.divisions[div][bu][app][env][subapp][cloud]:
                self.divisions[div][bu][app][env][subapp][cloud][region] = {}
                self.divisions[div][bu][app][env][subapp][cloud][region]['CVO HA'] = {}
                self.divisions[div][bu][app][env][subapp][cloud][region]['CVO'] = {}
                self.divisions[div][bu][app][env][subapp][cloud][region]['CVO HA']['RW'] = False
                self.divisions[div][bu][app][env][subapp][cloud][region]['CVO HA']['DP'] = False
                self.divisions[div][bu][app][env][subapp][cloud][region]['CVO']['RW'] = False
                self.divisions[div][bu][app][env][subapp][cloud][region]['CVO']['DP'] = False

            self.clusterdata[item] = ClusterData(item, self, **self.cluster_details[item])

    def go(self):
        for cluster in self.clusterdata.values():
            cluster.gather_data()

        self.build_volume_sheet()
        self.build_usage_sheet()
        self.build_totals_sheet()

        self.workbook.close()
        logging.info(f"Data saved to {self.filename}")

    def build_totals_sheet(self):
        self.totals_ws.write('A1', "Type")
        self.totals_ws.set_column(0, 0, 17)        
        self.totals_ws.write('B1', "Total Provisioned (Licensing) (TiB)")
        self.totals_ws.set_column(1, 1, 31.5)        
        self.totals_ws.write('C1', "Used (TiB)")
        self.totals_ws.set_column(2, 2, 14)        
        self.totals_ws.write('D1', "Percent Used")
        self.totals_ws.set_column(3, 3, 13)        

        self.totals_ws.write('A2', "Azure CVO RW")
        self.totals_ws.write_formula('B2', '=SUMIFS(usage_table[Provisioned (Licensing) TiB],usage_table[Cloud],"azure",usage_table[Cluster Type],"CVO",usage_table[Data Type],"RW")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('C2', '=SUMIFS(usage_table[Used TiB],usage_table[Cloud],"azure",usage_table[Cluster Type],"CVO",usage_table[Data Type],"RW")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('D2', '=IFERROR($C$2/$B$2, 0)', cell_format=self.cell_format_percentage)

        self.totals_ws.write('A3', "Azure CVO DP")
        self.totals_ws.write_formula('B3', '=SUMIFS(usage_table[Provisioned (Licensing) TiB],usage_table[Cloud],"azure",usage_table[Cluster Type],"CVO",usage_table[Data Type],"DP")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('C3', '=SUMIFS(usage_table[Used TiB],usage_table[Cloud],"azure",usage_table[Cluster Type],"CVO",usage_table[Data Type],"DP")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('D3', '=IFERROR($C$3/$B$3, 0)', cell_format=self.cell_format_percentage)

        self.totals_ws.write('A4', "Azure CVO HA RW")
        self.totals_ws.write_formula('B4', '=SUMIFS(usage_table[Provisioned (Licensing) TiB],usage_table[Cloud],"azure",usage_table[Cluster Type],"CVO HA",usage_table[Data Type],"RW")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('C4', '=SUMIFS(usage_table[Used TiB],usage_table[Cloud],"azure",usage_table[Cluster Type],"CVO HA",usage_table[Data Type],"RW")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('D4', '=IFERROR($C$4/$B$4, 0)', cell_format=self.cell_format_percentage)

        self.totals_ws.write('A5', "Azure CVO HA DP")
        self.totals_ws.write_formula('B5', '=SUMIFS(usage_table[Provisioned (Licensing) TiB],usage_table[Cloud],"azure",usage_table[Cluster Type],"CVO HA",usage_table[Data Type],"DP")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('C5', '=SUMIFS(usage_table[Used TiB],usage_table[Cloud],"azure",usage_table[Cluster Type],"CVO HA",usage_table[Data Type],"DP")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('D5', '=IFERROR($C$5/$B$5, 0)', cell_format=self.cell_format_percentage)

        self.totals_ws.write('A6', "Azure Totals")
        self.totals_ws.write_formula('B6', '=SUM($B2:$B5)', cell_format=self.cell_format_number)
        self.totals_ws.write_formula('C6', '=SUM($C2:$C5)', cell_format=self.cell_format_number)
        self.totals_ws.write_formula('D6', '=IFERROR($C$6/$B$6, 0)', cell_format=self.cell_format_percentage)

        self.totals_ws.write('A8', "AWS CVO RW")
        self.totals_ws.write_formula('B8', '=SUMIFS(usage_table[Provisioned (Licensing) TiB],usage_table[Cloud],"aws",usage_table[Cluster Type],"CVO",usage_table[Data Type],"RW")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('C8', '=SUMIFS(usage_table[Used TiB],usage_table[Cloud],"aws",usage_table[Cluster Type],"CVO",usage_table[Data Type],"RW")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('D8', '=IFERROR($C$8/$B$8, 0)', cell_format=self.cell_format_percentage)

        self.totals_ws.write('A9', "AWS CVO DP")
        self.totals_ws.write_formula('B9', '=SUMIFS(usage_table[Provisioned (Licensing) TiB],usage_table[Cloud],"aws",usage_table[Cluster Type],"CVO",usage_table[Data Type],"DP")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('C9', '=SUMIFS(usage_table[Used TiB],usage_table[Cloud],"aws",usage_table[Cluster Type],"CVO",usage_table[Data Type],"DP")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('D9', '=IFERROR($C$9/$B$9, 0)', cell_format=self.cell_format_percentage)

        self.totals_ws.write('A10', "AWS CVO HA RW")
        self.totals_ws.write_formula('B10', '=SUMIFS(usage_table[Provisioned (Licensing) TiB],usage_table[Cloud],"aws",usage_table[Cluster Type],"CVO HA",usage_table[Data Type],"RW")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('C10', '=SUMIFS(usage_table[Used TiB],usage_table[Cloud],"aws",usage_table[Cluster Type],"CVO HA",usage_table[Data Type],"RW")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('D10', '=IFERROR($C$10/$B$10, 0)', cell_format=self.cell_format_percentage)

        self.totals_ws.write('A11', "AWS CVO HA DP")
        self.totals_ws.write_formula('B11', '=SUMIFS(usage_table[Provisioned (Licensing) TiB],usage_table[Cloud],"aws",usage_table[Cluster Type],"CVO HA",usage_table[Data Type],"DP")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('C11', '=SUMIFS(usage_table[Used TiB],usage_table[Cloud],"aws",usage_table[Cluster Type],"CVO HA",usage_table[Data Type],"DP")',
                                     cell_format=self.cell_format_number)
        self.totals_ws.write_formula('D11', '=IFERROR($C$11/$B$11, 0)', cell_format=self.cell_format_percentage)

        self.totals_ws.write('A12', "AWS Totals")
        self.totals_ws.write_formula('B12', '=SUM($B8:$B11)', cell_format=self.cell_format_number)
        self.totals_ws.write_formula('C12', '=SUM($C8:$C11)', cell_format=self.cell_format_number)
        self.totals_ws.write_formula('D12', '=IFERROR($C$12/$B$12, 0)', cell_format=self.cell_format_percentage)



    def build_volume_sheet(self):

        # Headers for Volumes sheet
        # volumes_headers = [
        #     "Division", "BU", "Cluster", "App", "Environment", "SubApp", "Cloud",
        #     "Region", "Cluster Type", "Data Type", "Volume", "State", "Tags", "Provisioned Size (Licensing) [TiB]", "Used Size TiB", "%% used"
        # ]
        provision_col_header = "Provisioned (Licensing) TiB"
        used_col_header = "Used TiB"
        percentused_header = "%% Used"
        percentused_formula = f"=[@[{used_col_header}]]/[@[{provision_col_header}]] * 100"

        columns = [
                {'header': "Division", 'total_string': ''},
                {'header': "BU", 'total_string': ''},
                {'header': "Cluster", 'total_string': ''},
                {'header': "App", 'total_string': ''},
                {'header': "Environment", 'total_string': ''},
                {'header': "SubApp", 'total_string': ''},
                {'header': "Cloud", 'total_string': ''},
                {'header': "Region", 'total_string': ''},
                {'header': "Cluster Type", 'total_string': ''},
                {'header': "Data Type", 'total_string': ''},
                {'header': "Volume", 'total_string': ''},
                {'header': "State", 'total_string': ''},
                {'header': "Tags", 'total_string': ''},
                {'header': provision_col_header, 'total_function': 'sum'},
                {'header': used_col_header, 'total_function': 'sum'},
                {'header': percentused_header, 'formula': percentused_formula, 'total_function': 'average', 'format':self.cell_format_number}]

        number_format = [provision_col_header, used_col_header, percentused_header]
        # Write headers to Volumes sheet
        for col_num, header in enumerate(columns):
            self.volumes_ws.write(0, col_num, header['header'], self.cell_format)

        # Write data and track max column width
        volumes_col_widths = [len(header['header']) + 1 for header in columns]
        for row_num, row_data in enumerate(self.volume_data, start=1):
            for col_num, cell in enumerate(row_data):
                cell_format = self.cell_format
                if columns[col_num]['header'] in number_format:
                    cell_format = self.cell_format_number
                self.volumes_ws.write(row_num, col_num, cell, cell_format)
                cell_length = len(str(cell))
                if cell_length > volumes_col_widths[col_num]:
                    volumes_col_widths[col_num] = cell_length

        last_column = xlsxwriter.utility.xl_col_to_name(len(columns) - 1)
        table_range = f"A1:{last_column}{len(self.volume_data)+2}"
        self.volumes_ws.add_table(table_range, {
            'columns': columns,
            'style': 'Table Style Medium 9',
            'autofilter': True,
            'total_row': True,
            'name':'volume_table'
        })

        # Apply autofilter to Volumes sheet
        #self.volumes_ws.autofilter(0, 0, len(self.volume_data), len(columns) - 1)

        # Auto-size columns for Volumes sheet
        for col_num, width in enumerate(volumes_col_widths):
            self.volumes_ws.set_column(col_num, col_num, width + 4)

        # self.volumes_ws.autofit()
        self.volumes_ws.conditional_format(f"{last_column}2:{last_column}{len(self.volume_data) + 1}", {"type": "cell", "criteria": ">=", "value": 90, "format": self.cell_format_red})


    def build_usage_sheet(self):
        provision_col_header = "Provisioned (Licensing) TiB"
        used_col_header = "Used TiB"
        numbers_format = [provision_col_header, used_col_header, '%% Used']

        percentused_formula = f"=[@[{used_col_header}]]/[@[{provision_col_header}]] * 100"
        columns = [
                {'header': "Division", 'total_string': ''},
                {'header': "BU", 'total_string': ''},
                {'header': "App", 'total_string': ''},
                {'header': "Environment", 'total_string': ''},
                {'header': "SubApp", 'total_string': ''},
                {'header': "Cloud", 'total_string': ''},
                {'header': "Region", 'total_string': ''},
                {'header': "Cluster Type", 'total_string': ''},
                {'header': "Data Type", 'total_string': ''},
                {'header': provision_col_header, 'total_function': 'sum'},
                {'header': used_col_header, 'total_function': 'sum'},
                {'header': "% Used", 'formula': percentused_formula, 'total_function': 'average', 'format':self.cell_format_number}]

        volume_last_row = len(self.volume_data) + 1
        usage_data = []


        # Write headers to Usage sheet
        for col_num, header in enumerate(columns):
            self.usage_ws.write(0, col_num, header['header'], self.cell_format)

        # get the totals
        for div in self.divisions:
            for bu in self.divisions[div]:
                for app in self.divisions[div][bu]:
                    for env in self.divisions[div][bu][app]:
                        for subapp in self.divisions[div][bu][app][env]:
                            for cloud in self.divisions[div][bu][app][env][subapp]:
                                for region in self.divisions[div][bu][app][env][subapp][cloud]:
                                    for cluster_type in self.divisions[div][bu][app][env][subapp][cloud][region]:
                                        for data_type in self.divisions[div][bu][app][env][subapp][cloud][region][cluster_type]:
                                            if self.divisions[div][bu][app][env][subapp][cloud][region][cluster_type][data_type]:
                                                func_filter = f'Volumes!$A$2:$A${volume_last_row},"{div}",' \
                                                            f'Volumes!$B$2:$B${volume_last_row},"{bu}",' \
                                                            f'Volumes!$D$2:$D${volume_last_row},"{app}",' \
                                                            f'Volumes!$E$2:$E${volume_last_row},"{env}",' \
                                                            f'Volumes!$F$2:$F${volume_last_row},"{subapp}",' \
                                                            f'Volumes!$G$2:$G${volume_last_row},"{cloud}",' \
                                                            f'Volumes!$H$2:$H${volume_last_row},"{region}",' \
                                                            f'Volumes!$I$2:$I${volume_last_row},"{cluster_type}",' \
                                                            f'Volumes!$J$2:$J${volume_last_row},"{data_type}")'
                                                usage_data.append([div, bu, app, env, subapp, cloud, region, cluster_type, data_type,
                                                        f'=SUMIFS(Volumes!$N$2:$N${volume_last_row},{func_filter}',
                                                        f'=SUMIFS(Volumes!$O$2:$O${volume_last_row},{func_filter}',
                                                        ""])


        # Write data and track max column width
        usage_col_widths = [len(header['header']) + 1 for header in columns]
        for row_num, row_data in enumerate(usage_data, start=1):
            for col_num, cell in enumerate(row_data):
                cell_format = self.cell_format
                if columns[col_num]['header'] in numbers_format:
                    cell_format = self.cell_format_number
                self.usage_ws.write(row_num, col_num, cell, cell_format)
                cell_length = len(str(cell))
                if (not str(cell).startswith('=')) and cell_length > usage_col_widths[col_num]:
                    usage_col_widths[col_num] = cell_length


        # Add table with style and total row
        last_column = xlsxwriter.utility.xl_col_to_name(len(columns) - 1)
        table_range = f"A1:{last_column}{len(usage_data)+2}"
        self.usage_ws.add_table(table_range, {
            'columns': columns,
            'style': 'Table Style Medium 9',
            'autofilter': True,
            'total_row': True,
            'name':'usage_table'
        })

        # Auto-size columns for Usage sheet and get % Used column
        for col_num, width in enumerate(usage_col_widths):
            self.usage_ws.set_column(col_num, col_num, width + 2)
            if columns[col_num]['header'] == "% Used":
                percentused_column = xlsxwriter.utility.xl_col_to_name(col_num)

        # Set
        self.usage_ws.conditional_format(f"{percentused_column}2:{percentused_column}{len(usage_data) + 2}", {"type": "cell", "criteria": ">=", "value": 90, "format": self.cell_format_red})


class ClusterData:
    def __init__(self, clustername: str, app_instance: AppClass, **kwargs):
        self.name = clustername
        self.cluster_type = ''
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.app_instance = app_instance
        self.data_totals = {}
        self.data_totals['DP'] = False
        self.data_totals['RW'] = False

    def gather_data(self):
        logging.info(f'Gathering data for {self.name}')
        user, enc = self.app_instance.config.get_user('clusters', self.name)
        try:
            with HostConnection(self.ip, username=user, password=enc, verify=False):
                cluster = Cluster()

                cluster.get()

                nodes = list(Node.get_collection(fields="ha"))
                if len(nodes) > 1 and nodes[0]['ha']['enabled']:
                    self.cluster_type = 'CVO HA'
                else:
                    self.cluster_type = 'CVO'

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
                    self.app_instance.divisions[self.div][self.bu][self.app][self.env][self.subapp][self.cloud][self.region][self.cluster_type][volume['type'].upper()] = True
                    self.data_totals[volume['type'].upper()] = True
                    self.app_instance.volume_data.append([self.div,
                                                 self.bu,
                                                 self.name,
                                                 self.app,
                                                 self.env,
                                                 self.subapp,
                                                 self.cloud,
                                                 self.region,
                                                 self.cluster_type,
                                                 volume['type'].upper(),
                                                 volume['name'],
                                                 volume['state'],
                                                 ",".join(self.tags),
                                                 size,
                                                 used,
                                                 float(f"{(used / size) * 100:.3f}")])

        except Exception as e:
            logging.error(f"Could not retrieve data for {self.name} {volume['name']} {e}", exc_info=e)


if __name__ == '__main__':
    args = argp(script_name=script_name, description="gather volume and cluster stats, provisioned size and savings if changing to 80% and 90% autosize thresholds")
    config = Config(args.config_dir, args.output_dir)

    items = config.get_clusters(args.filter)

    APP = AppClass(script_name, items, config=config)
    APP.go()

