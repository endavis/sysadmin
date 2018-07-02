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

def listsnapmirror(vol):
  vol.getsnapmirrordest()
  if vol.snapdests:
    print('%s has the following destinations' % nvol.name)
    for i in vol.snapdests.values():
      print('   Dest: %s' % i['Destination Path'])

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
  naparser.add_argument('-off', '--offline', action='store_true',
                  help='offline the volume')
  naparser.add_argument('-on', '--online', action='store_true',
                  help='online the volume')
  naparser.add_argument('--delete', action='store_true',
                  help='delete the volumes')
  naparser.add_argument('-sr', '--releasesnapmirror', action='store_true',
                  help='release all snapmirror destinations')
  naparser.add_argument('-sl', '--listsnapmirror', action='store_true',
                  help='list all snapmirror destinations')
  naparser.add_argument('-d', '--details', action='store_true',
                  help='get details for volumes')
  naparser.add_argument('-cl', '--clones', action='store_true',
                  help='check if volumes has clones')

  args = naparser.parse_args()

  if not (args.unmount or args.mount or args.offline or args.online or args.delete or args.details or args.releasesnapmirror or args.listsnapmirror or args.clones or args.check):
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
      for vol in vols:
        print(vol)
      continue
    elif len(vols) == 0:
      print('%s - %s not found' % (cluster, vol))
      continue
    elif len(vols) == 1:
      nvol = vols[0]

    if nvol:
      if args.check:
        print('Found volume %s - %s - %s' % (cluster, nvol.svm.name, vol))
      if args.unmount:
        nvol.unmount()
      if args.mount:
        nvol.mount()
      if args.offline:
        nvol.offline()
      if args.online:
        nvol.online()
      if args.delete:
        nvol.delete()
      if args.releasesnapmirror:
        nvol.snapmirrorreleaseall()
      if args.listsnapmirror:
        listsnapmirror(nvol)
      if args.clones:
        nvol.checkclones()
      if args.details:
        print('%s,%s,%s,%s,%s,%s,%s' % (nvol.svm.cluster.name, nvol.svm.cluster.cname, nvol.svm.name, nvol.attr['Aggregate Name'], nvol.name, nvol.attr['Used Size'], nvol.attr['Total Physical Used Size']))

