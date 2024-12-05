'''
various utility functions for cloud links, etc
'''
# azure_resource_group_url_template = "https://portal.azure.com/#resource/subscriptions/${subscription_id}/resourceGroups/${resource_group_id}/providers/Microsoft.Compute/virtualMachines/${vmname}"
# azure_vm_url_template = "https://portal.azure.com/#resource/subscriptions/${subscription_id}/resourceGroups/${resource_group_id}/providers/Microsoft.Compute/virtualMachines/${vmname}"
azure_base_url = "https://portal.azure.com/#resource"

azure_provider_types ={
    'vm':'Microsoft.Compute/virtualMachines'
}

cloud_types = ['aws', 'azure', 'gcp', 'ibm']

cloud_account_names = {
    'azure': 'subscription',
    'aws': 'account',
    'ibm': 'account',
    'gcp': 'account'
}

def build_azure_id(sub_id, resource_group, resource_type='vm', resource_name=None):
    az_id = f"/subscriptions/{sub_id}/resourceGroups/{resource_group}"
    if resource_name:
        provider = azure_provider_types[resource_type]
        az_id = f"{az_id}/providers/{provider}/{resource_name}"
    return az_id

def build_azure_portal_link(resource_id):
    url = f"{azure_base_url}{resource_id}"
    return url

def get_cloud_account_name(cloud):
    return cloud_account_names[cloud]

def get_cloud_types():
    return cloud_types