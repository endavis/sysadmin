#/usr/bin/env python3
from NA import ClusterManager, approximate_size, naparser

def checksvm(svm):
  svm.fetchvolumes()
  size = 0
  for volume in svm.volumes.values():
    if not ('_root' in volume.name):
      if volume.attr['Volume State'] != 'offline':
        try:
          size = size + volume.attr['Used Size']
        except TypeError:
          for i in volume.attr:
            print(i, volume.attr[i])

  print('%s (%s) - Total size for volumes in %s: %s' % (svm.cluster.name, svm.cluster.cname, svm.name, approximate_size(size, False)))
  return size

def checkcluster(cluster):
  totalsize = 0
  for svm in cluster.svms.values():
    size = checksvm(svm)

    totalsize = totalsize + size

  print('%s (%s) - Total size of used data: %s' % (cluster.name, cluster.cname, approximate_size(totalsize, False)))

if __name__ == '__main__':
  naparser.add_argument('-s', '--svm',
                  help='the svm to total')
  naparser.add_argument('-cl', '--cluster',
                  help='the cluster of the svm, must be in the config')

  args = naparser.parse_args()
  CLMan = ClusterManager(args)

  if args.svm and args.cluster:
    if args.cluster in CLMan.clusters:
      cluster = CLMan.clusters[args.cluster]

      if args.svm in cluster.svms:
        checksvm(cluster.svms[args.svm])
      else:
        print('%s is not a valid svm' % args.svm)
        print('valid svms for cluster %s:' % (args.cluster))
        print('%s' % ", ".join(cluster.svms.keys()))
    else:
      print('%s is not a valid netapp cluster, valid clusters in config file are: %s' % (args.cluster, ", ".join(CLMan.clusters.keys())))
  elif args.cluster:
    if args.cluster in CLMan.clusters:
      checkcluster(CLMan.clusters[args.cluster])

    else:
      print('%s is not a valid netapp cluster, valid clusters in config file are: %s' % (args.cluster, ", ".join(CLMan.clusters.keys())))

  elif args.svm:
    svm = CLMan.findsvm(args.svm)
    if svm:
      checksvm(svm)
    else:
      print('%s is not a valid svm' % (args.svm))

  else:
    for cluster in CLMan.clusters.values():
      checkcluster(cluster)
