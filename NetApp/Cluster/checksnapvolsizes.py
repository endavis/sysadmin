#!/usr/bin/env python3
from NA import NAManager, naparser, approximate_size


def checkcluster(cluster):
  cluster.fetchpeers()
  cluster.fetchsnapmirrors()

  for mirror in cluster.snapmirrors:
    srcsvm = mirror['Source Path']['svm']
    srcvol = mirror['Source Path']['vol']
    svol = NApps.findvolume(srcvol, svm=srcsvm)

    destsvm = mirror['Destination Path']['svm']
    destvol = mirror['Destination Path']['vol']
    dvol = NApps.findvolume(destvol, svm=destsvm)

    if not svol:
      print('Could not find source volume - %s:%s' % (srcsvm, srcvol))

    if not dvol:
      print('Could not find destination volume - %s:%s' % (destsvm, destvol))

    if not dvol or not svol:
      continue

    if svol.attr['Volume Size'] != dvol.attr['Volume Size']:
      print('%s:%s:%s not equal to %s:%s:%s' % (srcsvm, srcvol, approximate_size(svol.attr['Volume Size'], False),
                                            destsvm, destvol, approximate_size(dvol.attr['Volume Size'], False)))

if __name__ == '__main__':
  naparser.add_argument('-n', '--netapp',
                  help='the cluster to check')
  args = naparser.parse_args()
  NApps = NAManager(args)

  if args.netapp:
    if args.netapp in NApps.netapps:
      checkcluster(NApps.netapps[args.netapp])
    else:
      print('%s is not a valid Netapp. Valid Netapps in config are %s.' % (args.netapp, ", ".join(NApps.netapps.keys())))

  else:
    for cluster in NApps.netapps.values():
      checkcluster(cluster)

