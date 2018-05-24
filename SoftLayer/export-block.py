#!/usr/bin/env python
import pprint
import configparser
import sys

import SoftLayer
from SoftLayer import BlockStorageManager
from sl.constants import convertstoragetoiops

config = configparser.ConfigParser()
config.read('softlayer.ini')

client = SoftLayer.create_client_from_env(username=config.get('General', 'username'), api_key=config.get('General', 'apikey'))

tfile = open('sl-block.psv', 'w')

SUBNETLU = {}
VDCS = {}
ALLVDCS = False

for vdc in config.items('VDCS'):
  if vdc[0].upper() == 'ALL':
    ALLVDCS = True
  else:
    VDCS[vdc[0].upper()] = True

for vdcn in config.items('VDCSUBNETID'):
  SUBNETLU[int(vdcn[1])] = vdcn[0].upper()

blockm = BlockStorageManager(client)

items = [
    'id',
    'username',
    'lunId',
    'capacityGb',
    'bytesUsed',
    'notes',
    'serviceResource.datacenter[name]',
    'serviceResourceBackendIpAddress',
    'activeTransactionCount',
    'replicationPartnerCount'
]
tmask = ','.join(items)

vols = blockm.list_block_volumes()

items = [
    'id',
    'username',
    'password',
    'capacityGb',
    'snapshotCapacityGb',
    'parentVolume.snapshotSizeBytes',
    'storageType.keyName',
    'serviceResource.datacenter[name]',
    'serviceResourceBackendIpAddress',
    'storageTierLevel',
    'provisionedIops',
    'lunId',
    'notes',
    'billingItem',
    'originalVolumeName',
    'originalSnapshotName',
    'originalVolumeSize',
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

#for volume in vols:
  #print('------------------------------------------')
  #print(volume)

  #if volume['serviceResource']['datacenter']['name'].upper() in VDCS or ALLVDCS == True:
    #print('Getting info for %s' % volume['username'])
    #try:
      #details = blockm.get_block_volume_details(volume['id'], mask=tmask)
    #except:
      #details = blockm.get_block_volume_details(volume['id'], mask=tmask)

    #try:
      #allowed = blockm.get_block_volume_access_list(volume['id'])
    #except:
      #allowed = blockm.get_block_volume_access_list(volume['id'])
      #if allowed['allowedVirtualGuests']:
        #pprint.pprint(allowed['allowedVirtualGuests'])

  #print(details)
  #print('allowed', allowed)
  #print('------------------------------------------')
#sys.exit(1)


tfile.write('SLID|UNIQUEID|DATACENTER|CREATED|TYPE|CAPACITY|IOPS|NOTES|SUBNETS|IPs|HARDWARE\n')

for volume in vols:
  #pprint.pprint(volume)
  if volume['serviceResource']['datacenter']['name'].upper() in VDCS or ALLVDCS == True:
    print('Getting info for %s' % volume['username'])
    try:
      details = blockm.get_block_volume_details(volume['id'], mask=tmask)
    except:
      details = blockm.get_block_volume_details(volume['id'], mask=tmask)
    try:
      allowed = blockm.get_block_volume_access_list(volume['id'])
    except:
      allowed = blockm.get_block_volume_access_list(volume['id'])
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
        if subnet['id'] in SUBNETLU:
          allowl.append(SUBNETLU[subnet['id']])
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

    iops = details['provisionedIops']

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
