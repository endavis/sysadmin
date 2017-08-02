#/usr/bin/env python3
from Cluster import ClusterManager, naparser
import sys
import os

#vol clone create -vserver svm_nakga01_prod -flexclone vol_wk_sfs_db_prd_data1a_ProdPrune -type RW -parent-volume vol_wk_sfs_db_prd_data1 -parent-snapshot ProdPrune


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
  naparser.add_argument('-n', '--name',
                  help='the name to append to the clone')
  naparser.add_argument('-s', '--snapshot',
                  help='the snapshot to use')
  naparser.add_argument('-i', '--input',
                  help='the input file of volumes',
                  default='volumes.txt')
  naparser.add_argument('-m', '--mount',
                  help='mount the volume')
  naparser.add_argument('-so', '--showonly', action='store_true',
                  help='only show the commands')


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

    elif nvol:
      nvol.clone(name=args.name, snapshot=args.snapshot, showonly=args.showonly)


