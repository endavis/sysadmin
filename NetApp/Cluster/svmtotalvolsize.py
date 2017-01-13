#/usr/bin/env python3

from NA import NAManager, approximate_size, naparser

if __name__ == '__main__':
  naparser.add_argument('-s', '--svm',
                  help='the svm to total')
  naparser.add_argument('-n', '--netapp',
                  help='the cluster of the svm, must be in the config')

  args = naparser.parse_args()
  NApps = NAManager(args)

  if args.svm:
    if args.netapp in NApps.netapps:
      cluster = NApps.netapps[args.netapp]

      if args.svm in cluster.svms:
        cluster.svms[args.svm].fetchvolumes()
        size = 0
        for volume in cluster.svms[args.svm].volumes.values():
            if not ('_root' in volume.name):
                size = size + volume.attr['Used Size']

        print('%s - Total size for volumes in %s: %s' % (cluster.name, args.svm, approximate_size(size, False)))
      else:
        print('%s is not a valid svm' % args.svm)
        print('valid svms for cluster %s:' % (args.netapp))
        print('%s' % ", ".join(cluster.svms.keys()))
    else:
      print('%s is not a valid netapp cluster, valid clusters in config file are: %s' % (args.netapp, ", ".join(NApps.netapps.keys())))
  else:
    for cluster in NApps.netapps.values():
      totalsize = 0
      for svm in cluster.svms.values():
        svm.fetchvolumes()
        size = 0
        for volume in svm.volumes.values():
          if not ('_root' in volume.name) and volume.name != 'vol0':
            if volume.attr['Volume State'] != 'offline':
              size = size + volume.attr['Used Size']

        totalsize = totalsize + size

        print('%s (%s) - Total size for volumes in %s: %s' % (cluster.name, cluster.cname, svm.name, approximate_size(size, False)))

      print('%s (%s) - Total size of used data: %s' % (cluster.name, cluster.cname, approximate_size(totalsize, False)))

