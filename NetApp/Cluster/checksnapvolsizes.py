#!/usr/bin/env python3
from NA import NAManager, naparser

if __name__ == '__main__':
  args = naparser.parse_args()
  NApps = NAManager(args)
  DAL = NApps.netapps['DAL']
  DAL.fetchpeers()
  DAL.fetchsnapmirrors()

  for mirror in DAL.snapmirrors:
    srcsvm = mirror['Source Path']['svm']
    srcvol = mirror['Source Path']['vol']
    svol = NApps.findvolume(srcvol, svm=srcsvm)

    destsvm = mirror['Destination Path']['svm']
    destvol = mirror['Destination Path']['vol']
    dvol = NApps.findvolume(destvol, svm=destsvm)

    if svol.attr['Volume Size'] != dvol.attr['Volume Size']:
      print('%s:%s:%s not equal to %s:%s:%s' % (srcsvm, srcvol, svol.attr['Volume Size'],
                                             destsvm, destvol, dvol.attr['Volume Size']))


