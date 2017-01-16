#!/usr/bin/env python3
from NA import ClusterManager, naparser
import os

if __name__ == '__main__':
  args = naparser.parse_args()
  CLMan = ClusterManager(args)

  for cluster in CLMan.clusters.values():
    for svm in cluster.svms.values():
      svm.fetchvolumes()

      for volume in svm.volumes.values():
        if not ('_root' in volume.name) and volume.name != 'vol0':
          if volume.attr['Space Guarantee Style'] != 'none':
            print('%s (%s) - Not thin - %-20s : %-40s' % (cluster.name, cluster.cname, svm.name, volume.name))
