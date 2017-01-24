#/usr/bin/env python3
from Cluster import ClusterManager, approximate_size, naparser
from dateutil.relativedelta import relativedelta
from datetime import timedelta
import time
import sys

def checksvm(svm, ndate):
  svm.fetchvolumes()
  cluster = svm.cluster
  for volume in svm.volumes.values():
    if not ('_root' in volume.name):
      if volume.attr['Volume State'] != 'offline':
        volume.fetchsnapshots()
        for snap in volume.snaps.values():
          stime = time.mktime(snap['Creation Time'])
          if ndate > stime:
            if args.csv:
              print("%s (%s),%s,%s,%s,%s,%s" % (cluster.name, cluster.cname, svm.name, volume.name, snap['Snapshot'], snap['Snapshot Size'],
                                                time.strftime("%m/%d/%Y %H:%M:%S", snap['Creation Time'])))
            else:
              print('Volume: %s - Snap: %s (%s) with time %s is before %s' % (volume.name, snap['Snapshot'], approximate_size(snap['Snapshot Size'], False),
                                                                            time.strftime("%m/%d/%Y %H:%M:%S", snap['Creation Time']),
                                                                            time.strftime("%m/%d/%Y %H:%M:%S", time.localtime(ndate))))

def checkcluster(cluster, ndate):
  totalsize = 0
  for svmname in sorted(cluster.svms.keys()):
    svm = cluster.svms[svmname]
    checksvm(svm, ndate)


if __name__ == '__main__':
  naparser.add_argument('-s', '--svm',
                  help='the svm to check')
  naparser.add_argument('-cl', '--cluster',
                  help='the cluster to check')
  naparser.add_argument('-d', '--date',
                  help='the date in "01/01/2016 14:22:00" format')
  naparser.add_argument('-csv', action='store_true',
                  help="output in comma delimited format")

  args = naparser.parse_args()

  if not args.date:
    print('date is a required filed')
    naparser.print_help()
    sys.exit(1)

  CLMan = ClusterManager(args)

  tst = time.strptime(args.date, "%m/%d/%Y %H:%M:%S")

  ndate = time.mktime(tst)

  if args.svm and args.cluster:
    if args.cluster in CLMan.clusters:
      cluster = CLMan.clusters[args.cluster]

      if args.svm in cluster.svms:
        checksvm(cluster.svms[args.svm], ndate)
      else:
        print('%s is not a valid svm' % args.svm)
        print('valid svms for cluster %s:' % (args.cluster))
        print('%s' % ", ".join(cluster.svms.keys()))
    else:
      print('%s is not a valid netapp cluster, valid clusters in config file are: %s' % (args.cluster, ", ".join(CLMan.clusters.keys())))
  elif args.cluster:
    if args.cluster in CLMan.clusters:
      checkcluster(CLMan.clusters[args.cluster], ndate)

    else:
      print('%s is not a valid netapp cluster, valid clusters in config file are: %s' % (args.cluster, ", ".join(CLMan.clusters.keys())))

  elif args.svm:
    svm = CLMan.findsvm(args.svm)
    if svm:
      checksvm(svm, ndate)
    else:
      print('%s is not a valid svm' % (args.svm))

  else:
    for cluster in CLMan.clusters.values():
      checkcluster(cluster, ndate)
