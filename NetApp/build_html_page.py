"""

"""
from pathlib import Path

from yattag import Doc, indent

#from workbook import SpaceWorkbook
from netapp_ontap import HostConnection, utils
from netapp_ontap.resources import Cluster, Node, Svm, IpInterface, CifsService

from libs.config import Config
from libs.parseargs import argp
from libs.cloud_utils import build_azure_id, build_azure_portal_link, get_cloud_types
from libs.log import setup_logger


style_file = 'style.txt'

logger = setup_logger()
logger.setLevel('INFO')
#utils.LOG_ALL_API_CALLS = 1

script = """
        const envButtons = document.querySelectorAll('.env-button');
        document.addEventListener('DOMContentLoaded', function() {
            openDetailsToButtons();
        }, false);

        envButtons.forEach(button => {
            button.addEventListener('click', function() {
                openActiveTrees(this.id);
            });
        });
        function openDetailsToButtons() {
            const activeElements = document.querySelectorAll('.button-stop');
            activeElements.forEach(element => {
                let open_flag = true;
                let parent = element.closest('details');
                parent = parent.parentElement.closest('details');
                while (parent) {
                    parent.open = true;
                    parent = parent.parentElement.closest('details');
                }
            });
        }

        function openActiveTrees(buttonid) {
            active_class = '.' + buttonid.replace('button', 'active');
            stop_class = 'button-stop';
            const activeElements = document.querySelectorAll(active_class);
            activeElements.forEach(element => {
                open_flag = !element.open;
                let parent = element.closest('details');

                while (parent) {
                    if (!open_flag && parent.classList.contains(stop_class)) {
                        parent.open = true;
                        break;
                    } else {
                        parent.open = open_flag;
                    }
                    parent = parent.parentElement.closest('details');
                }
                if (parent) {
                    parent.open = open_flag;
                }
            });
        };
"""

APP = None

class AppClass:
    def __init__(self, name, clusters, config):
        self.config = config
        self.name = name
        self.cluster_details = clusters
        self.clusterdata = {}
        self.divisions = {}
        self.counts = {}
        self.counts['ha'] = 0
        self.counts['sn'] = 0
        self.counts['aiqums'] = 0
        self.counts['connectors'] = 0
        self.button_ids =[]

        self.doc, self.tag, self.text = Doc().tagtext()
        self.build_app()

    def build_app(self):
        self.counts['aiqums'] = self.config.count('aiqums', 'ip')
        self.counts['connectors'] = self.config.count('connectors', 'ip')
        for item in self.cluster_details:
            self.clusterdata[item] = ClusterData(item, self, **self.cluster_details[item])
            cluster = self.clusterdata[item]

            if len(list(cluster.fetched_data['nodes'].keys())) > 1:
                self.counts['ha'] += 1
            else:
                self.counts['sn'] += 1

            if cluster.div not in self.divisions:
                self.divisions[cluster.div] = {}
            div = self.divisions[cluster.div]

            if cluster.bu not in div:
                div[cluster.bu] = {}
            bu = div[cluster.bu]

            if cluster.app not in bu:
                bu[cluster.app] = {}
            app = bu[cluster.app]

            if cluster.env not in app:
                app[cluster.env] = {}
            env = app[cluster.env]

            if cluster.subapp not in env:
                env[cluster.subapp] = {}
            env = env[cluster.subapp]

            if cluster.cloud not in env:
                env[cluster.cloud] = {}
            cloud = env[cluster.cloud]

            if cluster.region not in cloud:
                cloud[cluster.region] = {}
            region = cloud[cluster.region]

            region[cluster.name] = cluster
            if cluster.ele_class:
                self.button_ids.append(cluster.ele_class)

    def format_azure_info(self, azure_info):
        self.format_table_row_text('Azure Subscription Name', azure_info['location'])
        self.format_table_row_text('Azure Subscription ID', self.config.data['azure'][azure_info['location']]['id'])
        sub_id = self.config.data['azure'][azure_info['location']]['id']
        resource_group_id = build_azure_id(sub_id, azure_info['resource_group'])
        resource_group_url = build_azure_portal_link(resource_group_id)
        self.format_table_row_link('Azure Resource Group', resource_group_id, resource_group_url)
        if 'vmname' in azure_info:
            self.format_table_row_text('Azure VM Name', azure_info['vmname'])
            vmlink_id = build_azure_id(sub_id, azure_info['resource_group'], resource_name=azure_info['vmname'])
            vmlink_url = build_azure_portal_link(vmlink_id)
            self.format_table_row_link('Azure VM', vmlink_id, vmlink_url)

    def format_table_row_text(self, *args, header=False, error=False):
        if error:
            kwargs = {'klass':'error'}
        else:
            kwargs = {}
        with self.tag('tr'):
            for item in args:
                with self.tag('th' if header else 'td', **kwargs):
                    self.text(item)

    def format_table_row_link(self, col1, col2, link=None):
        with self.tag('tr'):
            with self.tag('td'):
                self.text(col1)
            with self.tag('td'):
                with self.tag('a', ('href', link)):
                    self.text(col2)

    def format_generic_cloud_item(self, item_type, item):
        with self.tag('li'):
            with self.tag('details'):
                with self.tag('summary'):
                    with self.tag('a', ('href', f"https://{item['ip']}")):
                        self.text(item_type)
                with self.tag('ul'):
                    with self.tag('li'):
                        with self.tag('table', ('class', 'custom-table')):
                                self.format_table_row_text('IP', item['ip'])
                                self.format_table_row_link('Application', 'Link', f"https://{item['ip']}")
                                if 'azure' in item:
                                    self.format_azure_info(item['azure'])
                                #self.format_aws_info(aiqum)

    def format_ci(self, ci):
        with self.tag('li'):
            with self.tag('a', ('href', ci['url'])):
                self.text('Cloud Insights')

    def format_utilities(self, search_terms):
        ci = self.config.find_closest('cloudinsights', search_terms)
        if ci:
            self.format_ci(ci)
        aiqum = self.config.find_closest('aiqums', search_terms)
        if aiqum:
            self.format_generic_cloud_item('AIQUM', aiqum)
        connector = self.config.find_closest('connectors', search_terms)
        if connector:
            self.format_generic_cloud_item('Connector', connector)
        # deploy = self.config.get_utilities('deployservers', search_terms, ignore=['cloud'])
        # if deploy:
        #     self.format_deploy(deployservers)

    def gather_data(self):
        self.doc.asis('<!DOCTYPE html>')
        with self.tag('html', ('lang', 'en')):
                with self.tag('head'):
                    self.doc.asis('<meta charset="utf-8">')
                    self.doc.asis('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
                    with self.tag('title'):
                        self.text('GBS NetApps')
                    with self.tag('base', ('target', '_blank'), ('rel', 'noopener noreferrer')):
                        ...
                    with self.tag('style'):
                        with open(style_file) as sfile:
                            for line in sfile:
                                self.doc.asis(line)
                with self.tag('body'):
                    with self.tag('ul', ('class', 'tree')):
                        self.format_divisions()
                    with self.tag('script'):
                        self.doc.asis(script)

        result = indent(self.doc.getvalue())
        with open('test.html', 'w') as tfile:
            tfile.write(result)
        logger.info(f"Processed {self.counts['ha'] + self.counts['sn']} clusters")
        logger.info(f"   Single Node : {self.counts['sn']}")
        logger.info(f"   HA          : {self.counts['ha']}")

    def format_divisions(self):
        divisions = list(self.divisions.keys())
        divisions.sort()
        for division in divisions:
            search_terms = {'div':division}
            with self.tag('li'):
                with self.tag('details', ('open', '')):
                    with self.tag('summary'):
                        self.text(division)
                    with self.tag('ul'):
                        self.format_business_units(division, self.divisions[division], search_terms)

    def format_business_units(self, where, business_units, search_terms):
        business_units_list = list(business_units.keys())
        business_units_list.sort()
        for business_unit in business_units_list:
            new_search_terms = search_terms.copy()
            new_search_terms['bu'] = business_unit
            new_where = f"{where}-{business_unit}"
            with self.tag('li'):
                with self.tag('details'):
                    with self.tag('summary'):
                        with self.tag('table', ('class', 'noborder-table')):
                            with self.tag('tr'):
                                with self.tag('td'):
                                    self.text(business_unit)

                    with self.tag('ul'):
                        self.format_apps(new_where, business_units[business_unit], new_search_terms)

    def format_buttons(self, where):
        with self.tag('td'):
            with self.tag('button', ('class', 'env-button'), ('id', f"{where}-active")):
                self.text('Go to Active Cluster(s)')

    def format_apps(self, where, apps, search_terms):
        if len(apps.keys()) == 1 and '' in apps:
            new_where = f"{where}-"
            new_search_terms = search_terms.copy()
            new_search_terms['app'] = ''
            self.format_environments(new_where, apps[''], new_search_terms)
        else:
            apps_list = list(apps.keys())
            apps_list.sort()
            for app in apps_list:
                new_where = f"{where}-{app}"
                det_class = ''
                if new_where in self.button_ids:
                    det_class='button-stop'
                new_search_terms = search_terms.copy()
                new_search_terms['app'] = app
                with self.tag('li'):
                    with self.tag('details', ('class', det_class)):
                        with self.tag('summary'):
                            with self.tag('table', ('class', 'noborder-table')):
                                with self.tag('tr'):
                                    with self.tag('td'):
                                        self.text(app)
                                    if det_class:
                                        self.format_buttons(new_where)
                        with self.tag('ul'):
                            self.format_environments(new_where, apps[app], new_search_terms)

    def format_environments(self, where, environments, search_terms):
        environments_list = list(environments.keys())
        environments_list.sort()
        for environment in environments_list:
            det_class = ''
            new_where = f"{where}-{environment}".replace('/', '').replace('&', '')
            if new_where in self.button_ids:
                det_class='button-stop'

            new_search_terms = search_terms.copy()
            new_search_terms['env'] = environment
            with self.tag('li'):
                with self.tag('details', ('class', det_class)):
                    with self.tag('summary'):
                        with self.tag('table', ('class', 'noborder-table')):
                            with self.tag('tr'):
                                with self.tag('td'):
                                    self.text(environment)
                                if det_class:
                                    self.format_buttons(new_where)
                    with self.tag('ul'):
                        self.format_subapps(new_where, environments[environment], new_search_terms)

    def format_subapps(self, where, subapps, search_terms):
        if len(subapps.keys()) == 1 and '' in subapps:
            new_search_terms = search_terms.copy()
            new_search_terms['subapp'] = ''
            self.format_clouds(subapps[''], new_search_terms)
        else:
            subapps_list = list(subapps.keys())
            subapps_list.sort()
            for subapp in subapps_list:
                new_where = f"{where}-{subapp}"
                det_class = ''
                if new_where in self.button_ids:
                    det_class='button-stop'
                new_search_terms = search_terms.copy()
                new_search_terms['subapp'] = subapp
                with self.tag('li'):
                    with self.tag('details', ('class', det_class)):
                        with self.tag('summary'):
                            with self.tag('table', ('class', 'noborder-table')):
                                with self.tag('tr'):
                                    with self.tag('td'):
                                        self.text(subapp)
                                    if det_class:
                                        self.format_buttons(new_where)
                        with self.tag('ul'):
                            self.format_clouds(subapps[subapp], new_search_terms)

    def format_clouds(self, clouds, search_terms):
        clouds_list = list(clouds.keys())
        clouds_list.sort()
        for cloud in clouds_list:
            new_search_terms = search_terms.copy()
            new_search_terms['cloud'] = cloud
            with self.tag('li'):
                    with self.tag('details'):
                        with self.tag('summary'):
                            self.text(cloud.upper())
                        with self.tag('ul'):
                            self.format_regions(clouds[cloud], new_search_terms)

    def format_regions(self, regions, search_terms):
        regions_list = list(regions.keys())
        regions_list.sort()
        for region in regions_list:
            region_data = regions[region]
            new_search_terms = search_terms.copy()
            new_search_terms['region'] = region
            with self.tag('li'):
                    with self.tag('details'):
                        with self.tag('summary'):
                            self.text(region)
                        with self.tag('ul'):
                            self.format_utilities(new_search_terms)
                            self.format_netapps(region_data)

    def format_netapps(self, netapps):
        for netapp_name in netapps:
            netapps[netapp_name].format(self.tag, self.text)

class ClusterData:
    def __init__(self, clustername, app_instance, **kwargs):
        self.name = clustername
        self.cluster_type = ''
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.fetched_data = {}
        self.app_instance = app_instance
        self.html_tag = self.app_instance.tag
        self.html_text = self.app_instance.text
        self.ele_class = ''
        if hasattr(self, 'tags') and 'active' in self.tags:
            ele_class = f"{self.div}-{self.bu}-{self.app}-{self.env}{f'-{self.subapp}' if self.subapp else ''}"
            self.ele_class = ele_class.replace('&', '').replace('/', '')

        self.gather_data()

    def build_cloud_info(self):
        if hasattr(self, 'azure'):
            sub_id = config.data['azure'][self.azure['location']]['id']
            self.azure['sub_id'] = sub_id
            self.azure['resource_group_id'] = build_azure_id(sub_id, self.azure['resource_group'])
            self.azure['resource_group_url'] = build_azure_portal_link(self.azure['resource_group_id'])

    def gather_data(self):
        logger.info(f'gathering data for {self.name}')
        self.build_cloud_info()

        with HostConnection(self.ip, username='cvomon', password=config.settings['users']['cvomon']['enc'], verify=False):
            cluster = Cluster()

            cluster.get()
            self.fetched_data['cluster'] = cluster.to_dict()

            nodes = list(Node.get_collection(fields="*"))
            self.fetched_data['nodes'] = {}
            for node in nodes:
                self.fetched_data['nodes'][node['name']] = node.to_dict()

            svms = list(Svm.get_collection(fields="*"))
            self.fetched_data['svms'] = {}
            for svm in svms:
                self.fetched_data['svms'][svm['name']] = svm.to_dict()

            ipinterfaces = list(IpInterface.get_collection(fields="*"))
            self.fetched_data['interfaces'] = {}
            for interface in ipinterfaces:
                self.fetched_data['interfaces'][interface['name']] = interface.to_dict()

            cifsservices = list(CifsService.get_collection(fields="*"))
            self.fetched_data['cifs'] = {}
            for cifserver in cifsservices:
                self.fetched_data['cifs'][cifserver['name']] = cifserver.to_dict()

            # pprint.pprint(self.fetched_data)

    def format(self, tag, text):
        logger.info(f"Cluster: {self.name}")
        active = False
        if hasattr(self, 'tags') and 'active' in self.tags:
            active = True
        with self.html_tag('li'):
            with self.html_tag('details', ('class', f'{self.ele_class}-active' if self.ele_class else '')):
                with self.html_tag('summary'):
                    with self.html_tag('table'):
                        with self.html_tag('tr'):
                            with self.html_tag('td'):
                                self.html_text(self.name)
                            if active:
                                with self.html_tag('td', ('class', 'active')):
                                    self.html_text('Active')

                    # self.html_text(f"{self.name}{active}")
                with self.html_tag('ul'):
                    # format cloud data
                    self.format_netapp_cloud_info()
                    self.format_netapp_cluster_info()
                    self.format_netapp_vservers_info()
                    self.format_netapp_nodes()

    def format_netapp_cloud_info(self):
        for cloud in get_cloud_types():
            if hasattr(self, cloud):
                with self.html_tag('li'):
                    with self.html_tag('details'):
                        with self.html_tag('summary'):
                            self.html_text(f"{cloud.title()} Information")
                        with self.html_tag('ul'):
                            with self.html_tag('li'):
                                with self.html_tag('table', ('class', 'custom-table')):
                                    func_name = f"format_{cloud}_info"
                                    try:
                                        func = getattr(self.app_instance, func_name)
                                        func(getattr(self, cloud))
                                    except AttributeError:
                                        pass


    def format_netapp_cluster_info(self):
        management_link = f"https://{self.fetched_data['cluster']['management_interfaces'][0]['ip']['address']}"
        with self.html_tag('li'):
            with self.html_tag('details'):
                with self.html_tag('summary'):
                    with self.html_tag('a', ('href', management_link)):
                        self.html_text('Cluster')
                with self.html_tag('ul'):
                    with self.html_tag('li'):
                        with self.html_tag('table', ('class', 'custom-table')):
                            self.app_instance.format_table_row_text('Version', self.fetched_data['cluster']['version']['full'])
                            self.app_instance.format_table_row_text('Cluster Management IP', self.fetched_data['cluster']['management_interfaces'][0]['ip']['address'])
                            self.app_instance.format_table_row_link('System Manager', 'Link', management_link)
                            self.app_instance.format_table_row_link('SPI', 'Link', f"{management_link}/spi")
                    with self.html_tag('li'):
                        with self.html_tag('details'):
                            with self.html_tag('summary'):
                                self.html_text('DNS')
                            with self.html_tag('ul'):
                                with self.html_tag('li'):
                                    with self.html_tag('table', ('class', 'custom-table')):
                                        self.app_instance.format_table_row_text('Domains', ', '.join(self.fetched_data['cluster']['dns_domains']))
                                        for i, name_server in enumerate(self.fetched_data['cluster']['name_servers']):
                                            self.app_instance.format_table_row_text(f"Server {i + 1}", name_server)
                    with self.html_tag('li'):
                        with self.html_tag('details'):
                            with self.html_tag('summary'):
                                self.html_text('NTP')
                            with self.html_tag('ul'):
                                with self.html_tag('li'):
                                    with self.html_tag('table', ('class', 'custom-table')):
                                        if 'ntp_servers' in self.fetched_data['cluster']:
                                            for i, name_server in enumerate(self.fetched_data['cluster']['ntp_servers']):
                                                self.app_instance.format_table_row_text(f"Server {i + 1}", name_server)
                                        else:
                                            self.app_instance.format_table_row_text(f"None", error=True)


    def format_netapp_vservers_info(self):
        svm_list = list(self.fetched_data['svms'].keys())
        svm_list.sort()
        for svm in svm_list:
            svm_data = self.fetched_data['svms'][svm]
            logger.info(f"  SVM: {svm_data['name']}")
            if svm_data['state'] == 'stopped':
                state = " - State: Stopped"
            else:
                state = ''
            with self.html_tag('li'):
                with self.html_tag('details'):
                    with self.html_tag('summary'):
                        self.html_text(f'vserver {svm_data["name"]}{state}')
                    with self.html_tag('ul'):
                        self.format_netapp_vserver_interfaces_info(svm_data)
                        self.format_netapp_vserver_dns_info(svm_data)
                        self.format_netapp_vserver_smb_server_info(svm_data)

    def format_netapp_vserver_interfaces_info(self, svm_data):
        if 'ip_interfaces' not in svm_data:
            return
        with self.html_tag('li'):
            with self.html_tag('details'):
                with self.html_tag('summary'):
                    self.html_text('Interfaces')
                with self.html_tag('ul'):
                    with self.html_tag('li'):
                        with self.html_tag('table', ('class', 'custom-table')):
                            self.app_instance.format_table_row_text('LIF name', 'LIF IP', 'Home Node', header=True)
                            for svm_interface in svm_data['ip_interfaces']:
                                ip_interface = self.fetched_data['interfaces'][svm_interface['name']]
                                self.app_instance.format_table_row_text(ip_interface['name'],
                                                        f"{ip_interface['ip']['address']}/{ip_interface['ip']['netmask']}",
                                                        ip_interface['location']['home_node']['name'])

    def format_netapp_vserver_dns_info(self, svm_data):
        with self.html_tag('li'):
            with self.html_tag('details'):
                with self.html_tag('summary'):
                    self.html_text('DNS')
                with self.html_tag('ul'):
                    with self.html_tag('li'):
                        with self.html_tag('table', ('class', 'custom-table')):
                            self.app_instance.format_table_row_text('Domains', ', '.join(svm_data['dns']['domains']))
                            for i, name_server in enumerate(svm_data['dns']['servers']):
                                self.app_instance.format_table_row_text(f"Server {i + 1}", name_server)

    def format_netapp_vserver_smb_server_info(self, svm_data):
        if 'name' not in svm_data['cifs']:
            return
        cifs_data = self.fetched_data['cifs'][svm_data['cifs']['name']]
        with self.html_tag('li'):
            with self.html_tag('details'):
                with self.html_tag('summary'):
                    self.html_text('SMB Server')
                with self.html_tag('ul'):
                    with self.html_tag('li'):
                        with self.html_tag('table', ('class', 'custom-table')):
                            self.app_instance.format_table_row_text('Enabled', cifs_data['enabled'])
                            self.app_instance.format_table_row_text('Name', cifs_data['name'])
                            self.app_instance.format_table_row_text('Domain', cifs_data['ad_domain']['fqdn'])
                            self.app_instance.format_table_row_text('Domain', cifs_data['ad_domain']['organizational_unit'])
                    with self.html_tag('li'):
                        with self.html_tag('details'):
                            with self.html_tag('summary'):
                                self.html_text('Security')
                            with self.html_tag('ul'):
                                with self.html_tag('li'):
                                    with self.html_tag('table', ('class', 'custom-table')):
                                        items = [('Is Signing Required', 'smb_signing'),
                                                 ('Use start_tls for AD LDAP connection', 'use_start_tls'),
                                                 ('LM Compatibility Level', 'lm_compatibility_level'),
                                                 ('Is SMB Encryption Required', 'smb_encryption'),
                                                 ('Client Session Security', 'session_security'),
                                                 ('LDAP Referral Enabled For AD LDAP connections', 'ldap_referral_enabled'),
                                                 ('Use LDAPS for AD LDAP connection', 'use_ldaps'),
                                                 ('Encryption is required for DC Connections', 'encrypt_dc_connection'),
                                                 ('AES session key enabled for NetLogon channel', 'aes_netlogon_enabled'),
                                                 ('Try Channel Binding For AD LDAP Connections', 'try_ldap_channel_binding'),
                                                 ('Encryption Types Advertised to Kerberos', 'advertised_kdc_encryptions'),
                                                ]
                                        for (header, key) in items:
                                            if isinstance(cifs_data['security'][key], list):
                                                self.app_instance.format_table_row_text(header, ', '.join(cifs_data['security'][key]))
                                            else:
                                                self.app_instance.format_table_row_text(header, cifs_data['security'][key])

    def format_netapp_nodes(self):
        node_list = list(self.fetched_data['nodes'].keys())
        node_list.sort()
        for node in node_list:
            node_data = self.fetched_data['nodes'][node]
            self.format_netapp_node(node_data)


    def format_netapp_node(self, node_data):
        management_link = f"https://{node_data['management_interfaces'][0]['ip']['address']}"
        vm_id = None
        vm_url = None
        match self.cloud:
            case 'azure':
                short_name = node_data['name'].split('-')[0]
                node_number = int(node_data['name'].split('-')[1])
                vm_type = 'Azure VM'
                if len(self.fetched_data['nodes']) > 1:
                    vm_name = f"{short_name}-vm{node_number}"
                else:
                    vm_name = f"{short_name}"
                if hasattr(self, 'azure'):
                    vm_id = build_azure_id(self.azure['sub_id'], self.azure['resource_group'], resource_name=vm_name)
                    vm_url = build_azure_portal_link(vm_id)

            case _:
                vm_name = 'Unknown'

        with self.html_tag('li'):
            with self.html_tag('details'):
                with self.html_tag('summary'):
                    with self.html_tag('a', ('href', management_link)):
                        self.html_text(node_data['name'])
                with self.html_tag('ul'):
                    with self.html_tag('li'):
                        with self.html_tag('table', ('class', 'custom-table')):
                            self.app_instance.format_table_row_text('Node Management IP', node_data['management_interfaces'][0]['ip']['address'])
                            self.app_instance.format_table_row_text('Serial Number', node_data['serial_number'])
                            self.app_instance.format_table_row_link('System Manager', 'Link', management_link)
                            self.app_instance.format_table_row_link('SPI', 'Link', f"{management_link}/spi")
                            if 'vm_name' != 'Unknown' and vm_id and vm_url:
                                self.app_instance.format_table_row_text(f'{vm_type} Name', vm_name)
                                self.app_instance.format_table_row_link(vm_type, vm_id, vm_url)

if __name__ == '__main__':
    args = argp(description="build html page of endpoints and mostly static information")
    config = Config(args.data_dir, debug=args.debug)

    items = config.get_clusters(args.filter)
    # pprint.pprint(items)

    APP = AppClass('html', items, config)
    APP.gather_data()

