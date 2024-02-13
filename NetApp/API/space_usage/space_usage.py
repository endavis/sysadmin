import logging

from workbook import SpaceWorkbook
from netapp_ontap import HostConnection, utils
from netapp_ontap.resources import FileInfo, CifsShare, UnixUser, Svm, Volume, Cluster

from size_utils import approximate_size, convert_size

#logging.basicConfig(level=logging.DEBUG)
#utils.LOG_ALL_API_CALLS = 1

# ZUSCULTAXCST010
API_IP = '192.168.1.1'

letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

SWB = SpaceWorkbook('Stats.xlsx')

with HostConnection(API_IP, username="username", password="password", verify=False):
    cluster = Cluster()
    cluster.get()
    cluster_data = SWB.addcluster(cluster['name'])
    resource = Svm.find(name="svm*")
    # space.capacity_tier_footprint
    # space.performance_tier_footprint
    # space.local_tier_footprint
    args = {}
    args['svm.name'] = resource['name']
    args['is_svm_root'] = False
    args['fields'] = 'aggregates.name,space.footprint,space.capacity_tier_footprint,space.performance_tier_footprint,space.user_data'
    volumes = Volume.get_collection(**args)
    for volume in volumes:
        if 'tax' in volume['aggregates'][0]['name'].lower():
            vtype = 'TAX'
        elif 'doc' in volume['aggregates'][0]['name'].lower():
            vtype = 'DOCUMENT'
        elif 'app' in volume['aggregates'][0]['name'].lower():
            vtype = 'APP'
        else:
            vtype = 'UNKNOWN'
        cluster_data.addvolume(volume['name'], vtype, approximate_size(volume["space"]["performance_tier_footprint"] + volume["space"]["capacity_tier_footprint"], 
                                                                        newsuffix='GB', withsuffix=False),            
                                approximate_size(volume["space"]["performance_tier_footprint"], newsuffix='GB', withsuffix=False),
                                approximate_size(volume["space"]["capacity_tier_footprint"], newsuffix='GB', withsuffix=False))                                                                        
        # print('---------------------------------------')
    #     print(f'{"Name":<8} : {volume["name"]}')
    #     print(f'{"Type":<8} : {vtype}')
    #     print(f'{"Hot":<8} : {approximate_size(volume["space"]["performance_tier_footprint"], newsuffix="GB")}')
    #     print(f'{"Cold":<8} : {approximate_size(volume["space"]["capacity_tier_footprint"], newsuffix="GB")}')
    #     print(f'{"Total":<8} : {approximate_size(volume["space"]["performance_tier_footprint"] + volume["space"]["capacity_tier_footprint"], newsuffix="GB")}')

    # print('---------------------------------------')
    SWB.close()
