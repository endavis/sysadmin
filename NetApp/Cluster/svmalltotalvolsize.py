#/usr/bin/env python3

from NA import NAManager, approximate_size, naparser

if __name__ == '__main__':
  naparser.add_argument('-s', '--svm',
                  help='the svm to total')

  args = naparser.parse_args()
  NApps = NAManager(args)


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

