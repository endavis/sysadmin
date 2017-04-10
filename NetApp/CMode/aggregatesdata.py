#!/usr/bin/env python3
from Cluster import ClusterManager, naparser, approximate_size

def checkcluster(cluster):
  totalsize = 0
  aggrs = {}
  cluster.fetchaggrs()

  tkeys = cluster.aggregates.keys()
  tkeys.sort()

  for taggr in tkeys:
    aggr = cluster.aggregates[taggr]
    if not ('root' in aggr.name):
      print('%s,%f,%f,%f,%f' % (aggr.name, aggr.attr['Size'], aggr.attr['Used Size'], aggr.attr['Total Physical Used Size'], aggr.attr['Available Size']))

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
      print('%s is not a valid Netapp cluster. Valid Netapp clusters in config are %s.' % (args.cluster, ", ".join(CLMan.clusters.keys())))

  else:
    for cluster in CLMan.clusters.values():
      checkcluster(cluster)
