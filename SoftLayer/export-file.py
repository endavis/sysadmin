#!/usr/bin/env python
import pprint
import configparser

import SoftLayer
from SoftLayer import FileStorageManager
from sl.constants import convertstoragetoiops

config = configparser.ConfigParser()
config.read('softlayer.ini')

client = SoftLayer.create_client_from_env(username=config.get('General', 'username'), api_key=config.get('General', 'apikey'))

tfile = open('sl-file.psv', 'w')

SUBNETLU = {}
VDCS = {}

for vdc in config.items('VDCS'):
  VDCS[vdc[0].upper()] = True

for vdcn in config.items('VDCNETWORKS'):
  SUBNETLU[vdcn[1]] = vdcn[0].upper()

filem = FileStorageManager(client)

items = [
    'id',
    'username',
    'capacityGb',
    'bytesUsed',
    'notes',
    'serviceResource.datacenter[name]',
    'serviceResourceBackendIpAddress',
    'activeTransactionCount',
    'fileNetworkMountAddress'
]
tmask = ','.join(items)

vols = filem.list_file_volumes()

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
    'volumeStatus',
    'iops',
    'notes',
    'events',
    'billingItem',
    'lunId',
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

tfile.write('SLID|UNIQUEID|DATACENTER|CREATED|TYPE|CAPACITY|IOPS|NOTES|SUBNETS|IPs|HARDWARE\n')

for volume in vols:
  if volume['serviceResource']['datacenter']['name'].upper() in VDCS:
    print('Getting info for %s' % volume['username'])
    try:
      details = filem.get_file_volume_details(volume['id'], mask=tmask)
    except:
      details = filem.get_file_volume_details(volume['id'], mask=tmask)
    try:
      allowed = filem.get_file_volume_access_list(volume['id'])
    except:
      allowed = filem.get_file_volume_access_list(volume['id'])
      if allowed['allowedVirtualGuests']:
        pprint.pprint(allowed['allowedVirtualGuests'])

    #print('volume')
    #print('----------------------------')
    #print(volume)

    #print('details')
    #print('----------------------------')
    #print(details)

    allowl = []
    if allowed['allowedSubnets']:
      for subnet in allowed['allowedSubnets']:
        net = '%s/%s' % (subnet['networkIdentifier'], subnet['cidr'])
        if net in SUBNETLU:
          allowl.append(SUBNETLU[net])
        else:
          allowl.append(net)

    allowi = []
    if allowed['allowedIpAddresses']:
      for ip in allowed['allowedIpAddresses']:
        allowi.append(ip['ipAddress'])

    allowh = []
    if (allowed['allowedHardware']):
      for hardware in allowed['allowedHardware']:
        tmsg = hardware['fullyQualifiedDomainName'] + '[' + hardware['privateIpAddress']
        try:
          tmsg = tmsg + '-' + hardware['primaryIpAddress']
        except KeyError:
          pass
        tmsg = tmsg + ']'
        allowh.append(tmsg)

    iops = 0
    if details['storageType']['keyName'] == 'PERFORMANCE_FILE_STORAGE':
      iops = details['iops']
    else:
      iops = convertstoragetoiops(details['storageTierLevel'])

    try:
      volume['capacityGb']
    except KeyError:
      volume['capacityGb'] = 'UNK'

    if 'notes' in volume:
      notes = volume['notes']
    elif 'notes' in details:
      notes = details['notes']
    else:
      notes = ''

    if not ('billingItem' in details):
      createdate = 'Unknown'
    else:
      createdate = details['billingItem']['createDate']

    notes = notes.strip()
    notes = notes.replace('\n', ' ')
    tstr = "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n" % (volume['username'].strip(),
                                 volume['id'],
                                 volume['serviceResource']['datacenter']['name'].upper().strip(),
                                 createdate.strip(),
                                 details['storageType']['keyName'].strip(),
                                 volume['capacityGb'],
                                 iops.strip(),
                                 notes,
                                 ":".join(allowl),
                                 ":".join(allowi),
                                 ":".join(allowh))
    tfile.write(tstr)

tfile.close()
