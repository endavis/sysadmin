#/usr/bin/env python3
import os
import sys
from Cluster import ClusterManager, naparser

def read_file(volfile):
    """
    the file should be of the format <cluster>:<volume>
    """
    vols = []
    if os.path.exists(volfile):
      tfile = open(volfile)
      for line in tfile:
        line = line.strip()
        if not line or line[0] == '#':
          continue
        cls, vol = line.split(':')
        vols.append({'cluster':cls, 'vol':vol})

      return vols

    else:
      print('input file %s does not exist' % volfile)
      sys.exit(1)


def findvolume(volname, cluster=None, svm=None, exact=False):

    nvol = CLMan.findvolume(volname, cluster=cluster, svm=svm, exact=exact)

    if nvol:
      for volume in nvol:
        print('%-10s (%s) - %-20s - %s' % (volume.svm.cluster.name, volume.svm.cluster.cname, volume.svm.name, volume.name))
    else:
      print('could not find volume %s' % volname)

if __name__ == '__main__':
  naparser.add_argument('-v', '--volume',
                  help='the volume to find, a regex')
  naparser.add_argument('-cl', '--cluster',
                  help='the cluster of the svm, must be in the config (optional)')
  naparser.add_argument('-s', '--svm',
                  help='the svm the volume is located (optional)')
  naparser.add_argument('-i', '--input',
                  help='the input file of volumes',
                  default=None)
  naparser.add_argument('-e', '--exact',
                  help='show only exact names',
                  default=None)

  args = naparser.parse_args()
  CLMan = ClusterManager(args)

  if args.input:
    volumes = read_file(args.input)

    for volume in volumes:
       findvolume(volume['vol'], cluster=volume['cluster'], exact=True)

  elif args.volume:
    findvolume(args.volume, cluster=args.cluster, svm=args.svm, exact=args.exact)

