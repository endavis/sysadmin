"""

"""
import logging
import pprint
from string import Template

from yattag import Doc, indent

#from workbook import SpaceWorkbook
from netapp_ontap import HostConnection, utils
from netapp_ontap.resources import Disk, Cluster, Volume, Node, Aggregate, Svm, IpInterface, CifsService

from libs.config import Config
from libs.parseargs import argp
from libs.size_utils import approximate_size_specific, convert_size
from libs.cloud_utils import build_azure_id, build_azure_portal_link, get_cloud_types, get_cloud_account_name

style_file = 'style.txt'

#logging.basicConfig(level=logging.DEBUG)
#utils.LOG_ALL_API_CALLS = 1

# env_table[div][bu][env][region]
# <html>
# <header>
# </header>
# with body:
#   with <ul class='tree'>
#       for each $div:
#           with <li>:
#               with <details open>:
#                   <summary>$div</summary>
#                   with <ul class='tree'>
#                       for each $bu:
#                           with <li>
#                               with <details open>:
#                                   <summary>$bu</summary>
#                                   with <ul class='tree'>
#                                       for each $env
#                                           with <li>
#                                               with <details open>:
#                                                   <summary>$env</summary>
#                                                   with <ul class='tree'>
#                                                       <li cloudinsights>
#                                                       for each $region
#                                                           with <li>:
#                                                               with <details open>:
#                                                                   <summary>$region</summary>
#                                                                   <li bluexp_connector>
#                                                                   <li AIQUM>
#                                                                   for each $netapp:
#                                                                       <li $netapp>
#                   

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

        self.doc, self.tag, self.text = Doc().tagtext()
        self.build_app()

    def build_app(self):
        self.counts['aiqums'] = self.config.count('aiqums', 'ip')
        self.counts['connectors'] = self.config.count('connectors', 'ip')
        for item in self.cluster_details:
            # print(f"adding {item}")
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

        # pprint.pprint(self.divisions)
                
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
        with self.tag('html'):
                with self.tag('head'):
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

        result = indent(self.doc.getvalue())
        with open('test.html', 'w') as tfile:
            tfile.write(result)
        print(f"Processed {self.counts['ha'] + self.counts['sn']} clusters")
        print(f"   Single Node : {self.counts['sn']}")
        print(f"   HA          : {self.counts['ha']}")

    def format_divisions(self):
        for division in self.divisions:
            search_terms = [{'div':division}]
            with self.tag('li'):
                with self.tag('details', ('open', '')):
                    with self.tag('summary'):
                        self.text(division)
                    with self.tag('ul'):
                        self.format_business_units(self.divisions[division], search_terms)
    
    def format_business_units(self, business_units, search_terms):
        for business_unit in business_units:   
            new_search_terms = search_terms[:]
            new_search_terms.append({'bu':business_unit})
            with self.tag('li'):
                with self.tag('details'):
                    with self.tag('summary'):
                        self.text(business_unit)
                    with self.tag('ul'):
                        self.format_apps(business_units[business_unit], new_search_terms)

    def format_apps(self, apps, search_terms):
        if len(apps.keys()) == 1 and '' in apps:
            new_search_terms = search_terms[:]
            new_search_terms.append({'app':''})
            self.format_environments(apps[''], new_search_terms)
        else:
            for app in apps:   
                new_search_terms = search_terms[:]
                new_search_terms.append({'app':app})
                with self.tag('li'):
                    with self.tag('details'):
                        with self.tag('summary'):
                            self.text(app)
                        with self.tag('ul'):
                            self.format_environments(apps[app], new_search_terms)

    def format_environments(self, environments, search_terms):
        for environment in environments:
            new_search_terms = search_terms[:]
            new_search_terms.append({'env':environment})
            with self.tag('li'):
                with self.tag('details'):
                    with self.tag('summary'):
                        self.text(environment)
                    with self.tag('ul'):
                        self.format_subapps(environments[environment], new_search_terms)

    def format_subapps(self, subapps, search_terms):
        if len(subapps.keys()) == 1 and '' in subapps:
            new_search_terms = search_terms[:]
            new_search_terms.append({'subapp':''})            
            self.format_clouds(subapps[''], new_search_terms)
        else:
            for subapp in subapps:
                new_search_terms = search_terms[:]
                new_search_terms.append({'subapp':subapp})
                with self.tag('li'):
                    with self.tag('details'):
                        with self.tag('summary'):
                            self.text(subapp)
                        with self.tag('ul'):
                            self.format_clouds(subapps[subapp], new_search_terms)

    def format_clouds(self, clouds, search_terms):
        for cloud in clouds:
            new_search_terms = search_terms[:]
            new_search_terms.append({'cloud':cloud})            
            with self.tag('li'):
                    with self.tag('details'):
                        with self.tag('summary'):
                            self.text(cloud.upper())
                        with self.tag('ul'):
                            self.format_regions(clouds[cloud], new_search_terms)

    def format_regions(self, regions, search_terms):
        cloud_types = get_cloud_types()
        for region in regions:
            region_data = regions[region]
            new_search_terms = search_terms[:]
            new_search_terms.append({'region':region})   
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
        self.tag = self.app_instance.tag
        self.text = self.app_instance.text
        self.gather_data()

    def build_cloud_info(self):
        if hasattr(self, 'azure'):
            sub_id = config.data['azure'][self.azure['location']]['id']
            self.azure['sub_id'] = sub_id
            self.azure['resource_group_id'] = build_azure_id(sub_id, self.azure['resource_group'])
            self.azure['resource_group_url'] = build_azure_portal_link(self.azure['resource_group_id'])

    def gather_data(self):
        print(f'gathering data for {self.name}')
        self.build_cloud_info()
        
        with HostConnection(self.ip, username=config.settings['settings']['user']['name'], password=config.settings['settings']['user']['enc'], verify=False):
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
        print(f"Cluster: {self.name}")
        self.tag = tag
        self.text = text
        active = False
        if hasattr(self, 'tags') and 'active' in self.tags:
            active = True
        with self.tag('li'):
            with self.tag('details'):
                with self.tag('summary'):
                    with self.tag('table'):                    
                        with self.tag('tr'):
                            with self.tag('td'):
                                self.text(self.name)
                            if active:
                                with self.tag('td', ('class', 'active')):
                                    self.text('Active')

                    # self.text(f"{self.name}{active}")
                with self.tag('ul'):
                    # format cloud data
                    self.format_netapp_cloud_info()
                    self.format_netapp_cluster_info()
                    self.format_netapp_vservers_info()
                    self.format_netapp_nodes()

    def format_netapp_cloud_info(self):
        for cloud in get_cloud_types():
            if hasattr(self, cloud):
                with self.tag('li'):
                    with self.tag('details'):
                        with self.tag('summary'):
                            self.text(f"{cloud.title()} Information")
                        with self.tag('ul'):
                            with self.tag('li'):
                                with self.tag('table', ('class', 'custom-table')):
                                    func_name = f"format_{cloud}_info"
                                    try:
                                        func = getattr(self.app_instance, func_name)
                                        func(getattr(self, cloud))
                                    except AttributeError:
                                        pass


    def format_netapp_cluster_info(self):
        management_link = f"https://{self.fetched_data['cluster']['management_interfaces'][0]['ip']['address']}"
        with self.tag('li'):
            with self.tag('details'):
                with self.tag('summary'):
                    with self.tag('a', ('href', management_link)):
                        self.text('Cluster')
                with self.tag('ul'):
                    with self.tag('li'):
                        with self.tag('table', ('class', 'custom-table')):
                            self.app_instance.format_table_row_text('Version', self.fetched_data['cluster']['version']['full'])
                            self.app_instance.format_table_row_text('Cluster Management IP', self.fetched_data['cluster']['management_interfaces'][0]['ip']['address'])
                            self.app_instance.format_table_row_link('System Manager', 'Link', management_link)
                            self.app_instance.format_table_row_link('SPI', 'Link', f"{management_link}/spi")
                    with self.tag('li'):
                        with self.tag('details'):                        
                            with self.tag('summary'):
                                self.text('DNS')
                            with self.tag('ul'):
                                with self.tag('li'):
                                    with self.tag('table', ('class', 'custom-table')):
                                        self.app_instance.format_table_row_text('Domains', ', '.join(self.fetched_data['cluster']['dns_domains']))
                                        for i, name_server in enumerate(self.fetched_data['cluster']['name_servers']):
                                            self.app_instance.format_table_row_text(f"Server {i + 1}", name_server)
                    with self.tag('li'):
                        with self.tag('details'):
                            with self.tag('summary'):
                                self.text('NTP')
                            with self.tag('ul'):
                                with self.tag('li'):
                                    with self.tag('table', ('class', 'custom-table')):
                                        if 'ntp_servers' in self.fetched_data['cluster']:
                                            for i, name_server in enumerate(self.fetched_data['cluster']['ntp_servers']):
                                                self.app_instance.format_table_row_text(f"Server {i + 1}", name_server)
                                        else:
                                            self.app_instance.format_table_row_text(f"None", error=True)


    def format_netapp_vservers_info(self):
        for svm in self.fetched_data['svms']:
            svm_data = self.fetched_data['svms'][svm]
            print(f"  SVM: {svm_data['name']}")
            if svm_data['state'] == 'stopped':
                state = " - State: Stopped"
            else:
                state = ''
            with self.tag('li'):
                with self.tag('details'):
                    with self.tag('summary'):
                        self.text(f'vserver {svm_data["name"]}{state}')    
                    with self.tag('ul'):
                        self.format_netapp_vserver_interfaces_info(svm_data)
                        self.format_netapp_vserver_dns_info(svm_data)
                        self.format_netapp_vserver_smb_server_info(svm_data)

    def format_netapp_vserver_interfaces_info(self, svm_data):
        if 'ip_interfaces' not in svm_data:
            return
        with self.tag('li'):
            with self.tag('details'):                        
                with self.tag('summary'):
                    self.text('Interfaces')
                with self.tag('ul'):                        
                    with self.tag('li'):
                        with self.tag('table', ('class', 'custom-table')):
                            self.app_instance.format_table_row_text('LIF name', 'LIF IP', 'Home Node', header=True)      
                            for svm_interface in svm_data['ip_interfaces']:
                                ip_interface = self.fetched_data['interfaces'][svm_interface['name']]
                                self.app_instance.format_table_row_text(ip_interface['name'], 
                                                        f"{ip_interface['ip']['address']}/{ip_interface['ip']['netmask']}",
                                                        ip_interface['location']['home_node']['name']) 
    
    def format_netapp_vserver_dns_info(self, svm_data):
        with self.tag('li'):
            with self.tag('details'):                        
                with self.tag('summary'):
                    self.text('DNS')
                with self.tag('ul'):                        
                    with self.tag('li'):
                        with self.tag('table', ('class', 'custom-table')):
                            self.app_instance.format_table_row_text('Domains', ', '.join(svm_data['dns']['domains']))                                    
                            for i, name_server in enumerate(svm_data['dns']['servers']):
                                self.app_instance.format_table_row_text(f"Server {i + 1}", name_server)                

    def format_netapp_vserver_smb_server_info(self, svm_data):
        if 'name' not in svm_data['cifs']:
            return
        cifs_data = self.fetched_data['cifs'][svm_data['cifs']['name']]
        with self.tag('li'):
            with self.tag('details'):                        
                with self.tag('summary'):
                    self.text('SMB Server')
                with self.tag('ul'):                        
                    with self.tag('li'):
                        with self.tag('table', ('class', 'custom-table')):
                            self.app_instance.format_table_row_text('Enabled', cifs_data['enabled'])
                            self.app_instance.format_table_row_text('Name', cifs_data['name'])
                            self.app_instance.format_table_row_text('Domain', cifs_data['ad_domain']['fqdn'])
                            self.app_instance.format_table_row_text('Domain', cifs_data['ad_domain']['organizational_unit'])
                    with self.tag('li'):
                        with self.tag('details'):                        
                            with self.tag('summary'):
                                self.text('Security')
                            with self.tag('ul'):
                                with self.tag('li'):
                                    with self.tag('table', ('class', 'custom-table')):
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
        for node in self.fetched_data['nodes']:
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
                vm_name = f"{short_name}-vm{node_number}"
                if hasattr(self, 'azure'):
                    vm_id = build_azure_id(self.azure['sub_id'], self.azure['resource_group'], resource_name=vm_name)
                    vm_url = build_azure_portal_link(vm_id)
            
            case _:
                vm_name = 'Unknown'

        with self.tag('li'):
            with self.tag('details'):
                with self.tag('summary'):
                    with self.tag('a', ('href', management_link)):
                        self.text(node_data['name'])
                with self.tag('ul'):
                    with self.tag('li'):
                        with self.tag('table', ('class', 'custom-table')):
                            self.app_instance.format_table_row_text('Node Management IP', node_data['management_interfaces'][0]['ip']['address'])
                            self.app_instance.format_table_row_text('Serial Number', node_data['serial_number'])
                            self.app_instance.format_table_row_link('System Manager', 'Link', management_link)
                            self.app_instance.format_table_row_link('SPI', 'Link', f"{management_link}/spi")
                            if 'vm_name' != 'Unknown' and vm_id and vm_url:
                                self.app_instance.format_table_row_text(f'{vm_type} Name', vm_name)
                                self.app_instance.format_table_row_link(vm_type, vm_id, vm_url)                            

if __name__ == '__main__':
    args = argp(description="build html page of endpoints and mostly static information")
    config = Config(args.data_dir, debug=False)

    items = config.get_clusters(args.filters)
    # pprint.pprint(items)

    APP = AppClass('html', items, config)
    APP.gather_data()

