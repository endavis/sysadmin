#!/usr/bin/env python
import argparse
import pprint
import configparser

import SoftLayer
from SoftLayer import FileStorageManager
from sl.constants import convertstoragetoiops

config = configparser.ConfigParser()
config.read('softlayer.ini')

client = SoftLayer.create_client_from_env(username=config.get('General', 'username'), api_key=config.get('General', 'apikey'))

naparser = argparse.ArgumentParser()
naparser.add_argument('volume', type=str, nargs='+',
                    help='volume to find')

if __name__ == '__main__':

  args = naparser.parse_args()
  print(args.volume)
  volumestofind = [x.upper() for x in args.volume]

  filem = FileStorageManager(client)

  storage= client.call('Network_Storage', 'getObject', id=28135103)
  pprint.pprint(storage)

  items = [
      'id',
      'username',
      'password',
      'capacityGb',
      'bytesUsed',
      'snapshotCapacityGb',
      'parentVolume.snapshotSizeBytes',
      'storageType.keyName',
      'serviceResource.datacenter[name]',
      'serviceResourceBackendIpAddress',
      'fileNetworkMountAddress',
      'storageTierLevel',
      'iops',
      'notes',
      'lunId',
      'events',
      'billingItem',
      'activeTransactionCount',
      'activeTransactions.transactionStatus[friendlyName]',
      'replicationPartnerCount',
      'replicationStatus',
      'replicationPartners[id,username,'
      'serviceResourceBackendIpAddress,'
      'serviceResource[datacenter[name]],'
      'replicationSchedule[type[keyname]]]',
  ]
  tmask = ','.join(items)

  vols = filem.list_file_volumes()

  for vol in vols:
    if vol['username'].upper() in volumestofind:
      details = filem.get_file_volume_details(vol['id'], mask=tmask)
      allowed = filem.get_file_volume_access_list(vol['id'])
      print('billing: %s' % details['billingItem'])
      print('-------------------------------------------')
      print(vol['username'])
      print(vol['serviceResource']['datacenter']['name'].upper())
      print(details['storageType']['keyName'])
      if details['storageType']['keyName'] == 'PERFORMANCE_FILE_STORAGE':
        print(details['iops'])
      else:
        print(convertstoragetoiops(details['storageTierLevel']))
      print(vol['capacityGb'])
      print('----   vol   ----')
      print(vol)
      print('---- details ----')
      print(details)
      print('---- allowed ----')
      print(allowed)
      print(allowed.keys())
      if (allowed['allowedSubnets']):
        print('---- subnets ----')
        for subnet in allowed['allowedSubnets']:
          net = '%s/%s' % (subnet['networkIdentifier'], subnet['cidr'])
          print(net)
      if (allowed['allowedIpAddresses']):
        print('----   ips   ----')
        for ip in allowed['allowedIpAddresses']:
          print(ip['ipAddress'])
      if (allowed['allowedHardware']):
        print('---- hardware ----')
        for hardware in allowed['allowedHardware']:
          tmsg = hardware['fullyQualifiedDomainName'] + '[' + hardware['privateIpAddress']
          try:
            tmsg = tmsg + '-' + hardware['primaryIpAddress']
          except KeyError:
            pass
          tmsg = tmsg + ']'
          print(tmsg)
      if (allowed['allowedVirtualGuests']):
        print('---- Virtual Guest ----')
        for vm in (allowed['allowedVirtualGuests']):
          pprint.pprint(vm)
