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
  naparser.add_argument('-cr', '--create', action='store_true',
                  help='create the snapshot')
  naparser.add_argument('-de', '--delete', action='store_true',
                  help='delete the snapshot')
  naparser.add_argument('-ch', '--check', action='store_true',
                  help='check input file for nonexistent volumes')
  naparser.add_argument('-i', '--input',
                  help='the input file of volumes',
                  default='volumes.txt')
  naparser.add_argument('-n', '--name',
                  help='the name of the snapshot')
  naparser.add_argument('-so', '--showonly', action='store_true',
                  help='only show the commands')

  args = naparser.parse_args()

  if not args.create and not args.delete and not args.check:
    print('please supply either the create, delete, or check argument')
    sys.exit(1)

  if args.create and args.delete and args.check:
    print('please supply either the create, delete, or check argument, but not all')
    sys.exit(1)

  if (args.create and args.delete) or (args.delete and args.check) or (args.create and args.check):
    print('please supply only one of the create, delete, or check arguments')
    sys.exit(1)

  if (args.delete or args.create) and not args.name:
    print('please supply a snapshot name')
    sys.exit(1)

  CLMan = ClusterManager(args)

  volumes = read_file(args.input)

  for volume in volumes:
    nvol = None
    vol = volume['vol']
    cluster = volume['cluster']
    vols = CLMan.findvolume(vol, cluster=cluster)
    if vols:
      nvol = vols[0]
    if args.check:
      if not nvol:
        print('%s - %s not found' % (cluster, vol))

    elif args.create:
      if nvol:
        nvol.createsnap(args.name, showonly=args.showonly)

    elif args.delete:
      if nvol:
        nvol.deletesnap(args.name, showonly=args.showonly)
