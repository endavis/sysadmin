#!/usr/bin/env python3
"""
check to make sure volumes can be moved into softlayer based on their inodes
"""
from Cluster import ClusterManager, naparser, approximate_size
import os

def checkcluster(cluster):
  for svm in cluster.svms.values():
    svm.fetchvolumes()

    for volume in svm.volumes.values():
      if not ('_root' in volume.name) and volume.name != 'vol0' and volume.attr['Volume State'] != 'offline':
        size = approximate_size(volume.attr['Volume Size'], False, "GB", False)
        usedsize = approximate_size(volume.attr['Used Size'], False, "GB", False)
        for limit in nkeys:
          if size >= limit:
            if int(volume.attr['Files Used (for user-visible data)']) > vollimitsGB[limit]:
              outfile.write('%s (%s),Increase Size for inodes,%-20s,%-40s,%s,%s\n' % (cluster.name, cluster.cname, svm.name, volume.name,
                    approximate_size(volume.attr['Volume Size'], False, "GB"),
                    volume.attr['Files Used (for user-visible data)']))
            break

        if usedsize > 12000:
            outfile.write('%s (%s),Volume Used Size,%-20s,%-40s,%s,%s\n' % (cluster.name, cluster.cname, svm.name, volume.name,
                    approximate_size(volume.attr['Used Size'], False, "GB"),
                    volume.attr['Files Used (for user-visible data)']))
        if size > 12000:
            outfile.write('%s (%s),Volume Overall Size,%-20s,%-40s,%s,%s\n' % (cluster.name, cluster.cname, svm.name, volume.name,
                    approximate_size(volume.attr['Volume Size'], False, "GB"),
                    volume.attr['Files Used (for user-visible data)']))



if __name__ == '__main__':
  naparser.add_argument('-cl', '--cluster',
                  help='the cluster to check')
  naparser.add_argument('-d', '--datadir', default='data',
                  help='the data directory to keep the stats')

  outfile = open("slrestrictions.csv", "w")

  vollimitsGB = {
    20:622484,
    40:1245084,
    80:2490263,
    100:3112863,
    250:7782300,
    500:15564695,
    1000:31876593,
  }

  args = naparser.parse_args()
  CLMan = ClusterManager(args)

  nkeys = sorted(vollimitsGB.keys())
  nkeys.reverse()

  if args.cluster:
    if args.cluster in CLMan.clusters:
      checkcluster(CLMan.clusters[args.cluster])

  else:
    for cluster in CLMan.clusters.values():
      checkcluster(cluster)
