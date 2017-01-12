#!/usr/bin/env python3
from NA import NAManager, naparser
import os

if __name__ == '__main__':
  args = naparser.parse_args()
  NApps = NAManager(args)

  for host in NApps.netapps.values():
    for vserver in host.vservers.values():
      vserver.getvolumes()

      for volume in vserver.volumes.values():
        if not ('_root' in volume.name) and volume.name != 'vol0':
          if volume.attr['Space Guarantee Style'] != 'none':
            print('Host: %s - Not thin provisioned - %-15s : %-40s' % (host.name, vserver.name, volume.name))
