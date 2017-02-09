#/usr/bin/env python3

from Cluster import ClusterManager, naparser

if __name__ == '__main__':
  naparser.add_argument('-v', '--volume', required=True,
                  help='the volume to find, a regex')
  naparser.add_argument('-cl', '--cluster',
                  help='the cluster of the svm, must be in the config (optional)')
  naparser.add_argument('-s', '--svm',
                  help='the svm the volume is located (optional)')

  args = naparser.parse_args()
  CLMan = ClusterManager(args)
  if args.volume:

    nvol = CLMan.findvolume(args.volume, cluster=args.cluster, svm=args.svm, exact=False)

    if nvol:
      for volume in nvol:
        print('%-10s (%s) - %-20s - %s' % (volume.svm.cluster.name, volume.svm.cluster.cname, volume.svm.name, volume.name))

