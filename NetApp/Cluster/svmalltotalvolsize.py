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
      host = NApps.netapps[args.netapp]

      if args.svm in host.vservers:
        host.vservers[args.svm].getvolumes()
        size = 0
        for volume in host.vservers[args.svm].volumes.values():
            if not ('_root' in volume.name):
                size = size + volume.attr['Used Size']

        print('%s - Total size for volumes in %s: %s' % (host.name, args.svm, approximate_size(size, False)))
      else:
        print('%s is not a valid svm' % args.svm)
        print('valid svms for host %s:' % (args.netapp))
        print('%s' % ", ".join(host.vservers.keys()))
    else:
      print('%s is not a valid netapp cluster, valid hosts in config file are: %s' % (args.netapp, ", ".join(NApps.netapps.keys())))
  else:
    for host in NApps.netapps.values():
      totalsize = 0
      for vserver in host.vservers.values():
        vserver.getvolumes()
        size = 0
        for volume in vserver.volumes.values():
          if not ('_root' in volume.name) and volume.name != 'vol0':
            if volume.attr['Volume State'] != 'offline':
              size = size + volume.attr['Used Size']

        totalsize = totalsize + size

        print('Host: %s - Total size for volumes in %s: %s' % (host.name, vserver.name, approximate_size(size, False)))

      print('Host: %s - Total size of used data: %s' % (host.name, approximate_size(totalsize, False)))

