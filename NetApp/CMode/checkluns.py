#!/usr/bin/env python3
from Cluster import ClusterManager, naparser
import os
"""
{'LUN Path': '/vol/vol_wk_sfs_Perform_Data_mirror/sflperforms01', 'Volume Name': 'vol_wk_sfs_Perform_Data_mirror', 'Qtree Name': '""', 'LUN Name': 'sflperforms01', 'LUN Size': 700000000000.0, 'OS Type': 'windows', 'Space Reservation': 'enabled', 'Serial Number': '804pr?HDpwpB', 'Serial Number (Hex)': '38303470723f484470777042', 'Comment': 'V: drive on PerformsKGA01 - Versioned Files', 'Space Reservations Honored': 'false', 'Space Allocation': 'disabled', 'State': 'online', 'LUN UUID': 'e71a571a-721a-4c7a-b82e-3f8b27fd95f2', 'Mapped': 'unmapped', 'Block Size': '512', 'Device Legacy ID': '-', 'Device Binary ID': '-', 'Device Text ID': '-', 'Read Only': 'true', 'Fenced Due to Restore': 'false', 'Used Size': 694900000000.0, 'Maximum Resize Size': 1470000000000.0, 'Creation Time': '3/16/2011 11:37:29', 'Class': 'regular', 'Node Hosting the LUN': 'wk-sfs-dr-s-01', 'QoS Policy Group': '-', 'Clone': 'false', 'Clone Autodelete Enabled': 'false', 'Inconsistent import': 'false'}
"""

if __name__ == '__main__':
  args = naparser.parse_args()
  CLMan = ClusterManager(args)

  for cluster in CLMan.clusters.values():
    for svm in cluster.svms.values():
      svm.fetchvolumes()
      svm.fetchluns()

      for volume in svm.volumes.values():
        if volume.luns:
          if not ('_root' in volume.name) and volume.name != 'vol0' and volume.attr['Volume State'] != 'offline':
            for lun in volume.luns.values():
              try:
                if lun.attr['Used Size'] >= lun.attr['LUN Size']:
                  print("%s - %s - %s lun used greater than or equal to lun size" % (svm.name, volume.name, lun.name))
              except TypeError:
                print(lun.attr)

              if lun.attr['Used Size']/lun.attr['LUN Size'] > .8:
                print("%s - %s - %s lun used greater than 80%% size" % (svm.name, volume.name, lun.name))
