"""

"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import logging

from netapp_ontap import HostConnection
from netapp_ontap.resources import LicensePackage, Node

from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger
from libs.email import send_email

setup_logger()
#utils.LOG_ALL_API_CALLS = 1

script_name = Path(__file__).stem

APP = None

html_first = """
<html>
<head>
    <style>
    .red-white {
        background-color: red;
        color: white;
        padding: 5px;
        font-weight: bold;
    }
    .yellow-black {
        background-color: yellow;
        color: black;
        padding: 5px;
        font-weight: bold;
    }
    </style>
</head>
<body>"""

html_last = """</body>
</html>"""

class AppClass:
    def __init__(self, name, clusters, config):
        # print(clusters)
        self.config = config
        self.name = name
        self.cluster_details = clusters
        self.license_issues = []
        self.cluster_data = {}
        self.license_issues = []

        self.build_app()

    def build_app(self):
        for item in self.cluster_details:
            self.cluster_data[item] = ClusterData(item, self, **self.cluster_details[item])

    def go(self):
        for cluster in self.cluster_data.values():
            cluster.gather_data()
            cluster.process_data()

        mailfrom = self.config.settings['settings']['licensing']['mailfrom'] or "Unknown Email"
        mailto= self.config.settings['settings']['licensing']['mailto'] or "Unknown Email"

        high_priority = False

        if self.license_issues:
            email_body = [html_first]
            email_body.append('    <p>The following licenses should be checked</p>')
            for item in self.license_issues:
                owner = item['owner'] if 'owner' in item else 'Unknown'
                serial = item['serial number'] if 'serial number' in item else 'Unknown'
                license_type = item['license type'] if 'license type' in item else 'Unknown'
                days = item['days checked'] if 'days checked' in item else 'Unknown'
                if days < 0:
                    #email_body.append(f"- {item['cluster']} - {owner} - {serial} - {license_type} has expired {abs(days)} days ago on {item['expires']}!  ")
                    email_body.append(f"    <p class='red-white'>{item['cluster']} - {owner} - {serial} - {license_type} has expired {abs(days)} days ago on {item['expires']}!</p>")
                else:
                    #email_body.append(f"- {item['cluster']} - {owner} - {serial} - {license_type} expires in {days} days on {item['expires']}  ")
                    email_body.append(f"    <p class='yellow-black'>{item['cluster']} - {owner} - {serial} - {license_type} expires in {days} days on {item['expires']}.</p>")

            email_body.append(html_last)
            str_body = "\r\n".join(email_body)
            message_subject = f"{datetime.now().date()} : Licensing issues found"
            high_priority=True
        else:
            str_body = 'No licensing issues'
            message_subject = f'{datetime.now().date()} : No licensing issues found'

        send_email(self.config,
                    subject=message_subject,
                    body=str_body,
                    body_type='html',
                    mailfrom=mailfrom,
                    mailto=mailto,
                    high_priority=high_priority)


class ClusterData:
    def __init__(self, clustername, app_instance, **kwargs):
        self.name = clustername
        self.cluster_type = ''
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.fetched_data = {}
        self.app_instance = app_instance

    def gather_data(self):
        logging.info(f"{script_name} : Checking {self.name}")
        user, enc = self.app_instance.config.get_user('clusters', self.name)        
        try:
            with HostConnection(self.ip, username=user, password=enc, verify=False):
                self.fetched_data['licenses'] = []
                for license in LicensePackage.get_collection(fields="*"):
                    self.fetched_data['licenses'].append(license.to_dict())

                self.fetched_data['nodes'] = {}
                for node in Node.get_collection(fields="*"):
                    self.fetched_data['nodes'][node['name']] = node.to_dict()
                    self.fetched_data['nodes'][node['name']]['valid_license'] = False
        except Exception as e:
            logging.error(f"Could not retrieve events for {self.name} {e}")


    def process_data(self):
        days_to_check = 30
        license_type = 'ONTAP BYOL'
        current_time = datetime.now(timezone.utc)
        
        if not self.fetched_data['licenses']:
            self.app_instance.license_issues.append({'cluster':self.name,
                                                        'owner': '',
                                                        'error': 'Could not get licenses',
                                                        'days checked': -1,
                                                        'serial number':-1,
                                                        'expires':-1,
                                                        'license type': -1})
            return

        for license in self.fetched_data['licenses']:
            for item in license['licenses']:
                serial_number = item['serial_number']

                match serial_number:
                    # The following two licenses are updated by BlueXP daily
                    # with an expire time 14 days in the future
                    case sn if sn.startswith('9092'):
                        days_to_check = 13
                        license_type = 'ONTAP Cloud Capacity'
                    case sn if sn.startswith('2265'):
                        days_to_check = 13
                        license_type = 'Data Tiering'

                    # ONTAP select licenses have no expiration
                    case sn if sn.startswith('3200'):
                        license_type = 'ONTAP Select'

                if item['owner'] in self.fetched_data['nodes']:
                        self.fetched_data['nodes'][item['owner']]['has_license'] = True
                        self.fetched_data['nodes'][item['owner']]['license_type'] = license_type

                if 'expiry_time' in item and item['owner'] != 'none':
                    # has_license = True

                    expiry_time = datetime.fromisoformat(item['expiry_time'])

                    # Calculate the difference
                    delta = expiry_time - current_time

                    # Get the number of days
                    days_difference = delta.days

                    if days_difference < days_to_check:
                        self.app_instance.license_issues.append({'cluster':self.name,
                                                                 'owner': item['owner'],
                                                                 'error': 'Expiring license',
                                                                 'days checked': days_difference,
                                                                 'serial number':item['serial_number'],
                                                                 'expires':expiry_time,
                                                                 'license type': license_type})
                        if days_difference < 0:
                            #email_body.append(f"- {item['cluster']} - {owner} - {serial} - {license_type} has expired {abs(days)} days ago on {item['expires']}!  ")
                            logging.info(f"{self.name} - {item['owner']} - {item['serial_number']} - {license_type} has expired {abs(days_difference)} days ago on {expiry_time}!")
                        else:
                            #email_body.append(f"- {item['cluster']} - {owner} - {serial} - {license_type} expires in {days} days on {item['expires']}  ")
                            logging.info(f"{self.name} - {item['owner']} - {item['serial_number']} - {license_type} expires in {days_difference} days on {expiry_time}")



        for node in self.fetched_data['nodes']:

            if not 'has_license' in self.fetched_data['nodes'][node] or not self.fetched_data['nodes'][node]['has_license']:

                self.app_instance.license_issues.append({'cluster':self.name,
                                                        'node': node,
                                                        'error': 'No License',
                                                        'days checked': -1,
                                                        'serial number': self.fetched_data['nodes'][node]['serial_number'] if 'serial_number' in self.fetched_data['nodes'][node] else 'Unknown',
                                                        'expires': -1,
                                                        'license type': 'None'})



if __name__ == '__main__':

    args = argp(script_name=script_name, description="check clusters for licensing issues")
    config = Config(args.config_dir, args.output_dir)

    items = config.get_clusters(args.filter)

    APP = AppClass(script_name, items, config)
    APP.go()

