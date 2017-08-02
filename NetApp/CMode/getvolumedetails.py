#/usr/bin/env python3
from Cluster import ClusterManager, naparser
import sys
import os

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


if __name__ == '__main__':
  naparser.add_argument('-ch', '--check', action='store_true',
                  help='check input file for nonexistent volumes')
  naparser.add_argument('-i', '--input',
                  help='the input file of volumes',
                  default='volumes.txt')

  args = naparser.parse_args()

  CLMan = ClusterManager(args)

  volumes = read_file(args.input)

  for volume in volumes:
    vol = volume['vol']
    cluster = volume['cluster']
    nvol = CLMan.findvolume(vol, cluster=cluster)[0]
    if args.check:
      if not nvol:
        print('%s - %s not found' % (cluster, vol))
    else:
      if nvol:
        print('%s,%s,%s,%s,%s,%s' % (nvol.svm.cluster.name, nvol.svm.cluster.cname, nvol.svm.name, nvol.attr['Aggregate Name'], nvol.name, nvol.attr['Used Size']))

