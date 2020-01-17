#!/usr/bin/env python3
from Cluster import ClusterManager, naparser, approximate_size

#echo "name=JVM|Files|<process name 1>,value="$count1
#echo "name=JVM|Files|<process name 2>,value="$count2

def checkcluster(cluster):
  # Get cluster stats
  cpu, ops, bps, latency = cluster.fetchclusterstats()
  bps = int(bps)
  latency = int(latency)
  print('NETAPP|DAL09|Cluster,CPU %%=%s' % cpu)
  print('NETAPP|DAL09|Cluster,Total IOPs=%s' % ops)
  print('NETAPP|DAL09|Cluster,MBPS=%.2f' % (bps/1024/1024))
  print('NETAPP|DAL09|Cluster,Latency(ms)=%s' % (latency/1000))

  # Get aggregate stats
  cluster.fetchaggrs()

  tkeys = cluster.aggregates.keys()
  skeys = sorted(tkeys)

  for taggr in skeys:
    aggr = cluster.aggregates[taggr]
    if not ('root' in aggr.name):
      print('NETAPP|DAL09|Aggregates|%s,Total Space (GB)=%.2f' % (aggr.name, approximate_size(aggr.attr['Size'], newsuffix='GB', withsuffix=False)))
      print('NETAPP|DAL09|Aggregates|%s,Used Space (GB)=%.2f' % (aggr.name, approximate_size(aggr.attr['Used Size'], newsuffix='GB', withsuffix=False)))
      print('NETAPP|DAL09|Aggregates|%s,Percent Used(GB)=%.2d' % (aggr.name, (aggr.attr['Used Size']/aggr.attr['Size'])*100))


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
