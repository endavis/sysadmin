#!/usr/bin/env python3
from Cluster import ClusterManager, naparser, approximate_size
import os

def checkcluster(cluster):
  for svm in cluster.svms.values():
    svm.fetchvolumes()

    for volume in svm.volumes.values():
      if not ('_root' in volume.name) and volume.name != 'vol0' and volume.attr['Volume State'] != 'offline':
        if volume.attr['Space Guarantee Style'] != 'none':
          if args.csv:
            print('%s,%s,%s,%s,%s,%s' % (cluster.name, svm.name, volume.attr['Aggregate Name'], volume.name, volume.attr['Available Size']))
          else:
            print('%s (%s) - Not thin - %-20s : %-40s : %s' % (cluster.name, cluster.cname, svm.name, volume.name, approximate_size(volume.attr['Available Size'], False)))


if __name__ == '__main__':
  naparser.add_argument('-cl', '--cluster',
                  help='the cluster to check')
  naparser.add_argument('-csv', action='store_true',
                  help="output in comma delimited format")

  args = naparser.parse_args()
  CLMan = ClusterManager(args)

  if args.cluster:
    if args.cluster in CLMan.clusters:
      checkcluster(CLMan.clusters[args.cluster])
  else:
    for cluster in CLMan.clusters.values():
      checkcluster(cluster)
