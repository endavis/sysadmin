#!/usr/bin/env python3
from Cluster import ClusterManager, naparser, approximate_size

def checkcluster(cluster):
  totalsize = 0
  aggrs = {}
  for svmname in sorted(cluster.svms.keys()):
    svm = cluster.svms[svmname]
    svm.fetchvolumes()
    svm.fetchluns()

    for volume in svm.volumes.values():
      if not ('_root' in volume.name) and volume.name != 'vol0':
        if volume.attr['Space Guarantee Style'] != 'none':
          if len(volume.luns) > 0:
            continue
          if volume.attr['Volume State'] != 'offline':
            try:
              totalsize = totalsize + volume.attr['Available Size']
              aggr = volume.attr["Aggregate Name"]
              if not (aggr in aggrs):
                aggrs[aggr] = 0
              aggrs[aggr] = aggrs[aggr] + volume.attr['Available Size']

            except TypeError:
              print(volume.name, volume.attr['Available Size'])
            if args.csv:
              print('%s (%s),%s,%s,%s,%d' % (cluster.name, cluster.cname, svm.name, volume.name, volume.attr['Aggregate Name'], volume.attr['Available Size']))
            else:
              print('%s (%s) - Not thin - %-20s : %-12s : %s' % (cluster.name, cluster.cname, svm.name, approximate_size(volume.attr['Available Size'], False), volume.name))

  for aggr in sorted(aggrs.keys()):
    if args.csv:
      print('%s,%d' % (aggr, aggrs[aggr]))
    else:
      print('aggr %s would gain %s' % (aggr, approximate_size(aggrs[aggr], False)))

  if args.csv:
    print('%s (%s),%d' % (cluster.name, cluster.cname, totalsize))
  else:
    print('%s (%s) - %s more space if the above volumes were thin provisioned' % (cluster.name, cluster.cname, approximate_size(totalsize, False)))

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
