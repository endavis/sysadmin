#/usr/bin/env python3
from Cluster import ClusterManager, naparser
import sys
import os

#        print('%s,%s,%s,%s,%s,%s' % (nvol.svm.cluster.name, nvol.svm.cluster.cname, nvol.svm.name, nvol.attr['Aggregate Name'], nvol.name, nvol.attr['Used Size']))

def checkcluster(cluster):
  """
  get information for a specific cluster
  """
  for svm in cluster.svms.values():
    svm.fetchvolumes()
    for nvol in svm.volumes.values():
      print('%s,%s,%s,%s,%s,%s,%s' % (nvol.svm.cluster.name, nvol.svm.cluster.cname, nvol.svm.name, nvol.attr['Aggregate Name'], nvol.name, nvol.attr['Used Size'], nvol.attr['Total Physical Used Size']))

if __name__ == '__main__':
  naparser.add_argument('-cl', '--cluster',
                  help='the cluster to check')

  args = naparser.parse_args()

  CLMan = ClusterManager(args)

  if args.cluster:
    if args.cluster in CLMan.clusters:
      checkcluster(CLMan.clusters[args.cluster])

    else:
      print('%s is not a valid Netapp cluster. Valid Netapp clusters in config are %s.' % (args.cluster, ", ".join(CLMan.clusters.keys())))

  else:
    for cluster in CLMan.clusters.values():
      checkcluster(cluster)


