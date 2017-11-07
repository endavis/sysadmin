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
  naparser.add_argument('-m', '--mount', action='store_true',
                  help='mount the volumes')
  naparser.add_argument('-u', '--unmount', action='store_true',
                  help='unmount the volumes')
  naparser.add_argument('-o', '--offline', action='store_true',
                  help='offline the volume')
  naparser.add_argument('--delete', action='store_true',
                  help='delete the volumes')
  naparser.add_argument('-d', '--details', action='store_true',
                  help='get details for volumes')
  naparser.add_argument('-cl', '--clones', action='store_true',
                  help='check if volumes has clones')

  args = naparser.parse_args()

  if not (args.unmount or args.mount or args.offline or args.delete or args.details or args.clones or args.check):
    print('Please specifiy one of the options')
    sys.exit(1)

  CLMan = ClusterManager(args)

  volumes = read_file(args.input)

  for volume in volumes:
    vol = volume['vol']
    cluster = volume['cluster']
    vols = CLMan.findvolume(vol, cluster=cluster)
    nvol = None
    if len(vols) > 1:
      print('More than one volume found with the name %s' % vol)
      continue
    elif len(vols) == 0:
      print('%s - %s not found' % (cluster, vol))
      continue
    elif len(vols) == 1:
      nvol = vols[0]

    if nvol:
      if args.check:
        print('Found volume %s - %s' % (cluster, vol))
      if args.unmount:
        nvol.unmount()
      if args.mount:
        nvol.mount()
      if args.offline:
        nvol.offline()
      if args.delete:
        nvol.delete()
      if args.clones:
        nvol.checkclones()
      if args.details:
        print('%s,%s,%s,%s,%s,%s,%s' % (nvol.svm.cluster.name, nvol.svm.cluster.cname, nvol.svm.name, nvol.attr['Aggregate Name'], nvol.name, nvol.attr['Used Size'], nvol.attr['Total Physical Used Size']))

