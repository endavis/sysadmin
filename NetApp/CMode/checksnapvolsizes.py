#!/usr/bin/env python3
from Cluster import ClusterManager, naparser, approximate_size


def checkcluster(cluster):
  cluster.fetchpeers()
  cluster.fetchsnapmirrors()

  for mirror in cluster.snapmirrors:
    srcsvm = mirror['Source Path']['svm']
    srcvol = mirror['Source Path']['vol']
    svol = CLMan.findvolume(srcvol, svm=srcsvm)

    destsvm = mirror['Destination Path']['svm']
    destvol = mirror['Destination Path']['vol']
    dvol = CLMan.findvolume(destvol, svm=destsvm)

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
  naparser.add_argument('-cl', '--cluster',
                  help='the cluster to check')
  args = naparser.parse_args()
  CLMan = ClusterManager(args)

  if args.cluster:
    if args.cluster in CLMan.clusters:
      checkcluster(CLMan.clusters[args.cluster])
    else:
      print('%s is not a valid Netapp. Valid Netapps in config are %s.' % (args.cluster, ", ".join(CLMan.clusters.keys())))

  else:
    for cluster in CLMan.clusters.values():
      checkcluster(cluster)

