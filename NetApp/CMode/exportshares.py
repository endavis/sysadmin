#!/usr/bin/env python3
from Cluster import ClusterManager, naparser
import os

def checkcluster(cluster):
  for svm in cluster.svms.values():
    svm.fetchshares()
    if svm.shares:
      outfile = open('out/%s.csv' % svm.name, "w")
      outfile.write(','.join(['svm','server','name','full path','vol path','comment','permissions']) + '\n')
      for share in svm.shares.values():
        svmname = svm.name
        sharename = share.name
        path = share.attr['Path']
        server = share.attr['CIFS Server NetBIOS Name']

        if path == '/':
          continue

        fullpath = "\\\\" + "\\".join([server, sharename])
        if type(share.attr['Share ACL']) == type([]):
          permission = ';'.join(share.attr['Share ACL'])
        else:
          permission = share.attr['Share ACL']
        comment = share.attr['Share Comment']
        outfile.write(','.join([svmname, "\\\\" + server, sharename, fullpath, path, comment, permission]) + '\n')

      outfile.close()

if __name__ == '__main__':

  naparser.add_argument('-cl', '--cluster',
                  help='the cluster of the svm, must be in the config (optional)')

  args = naparser.parse_args()
  CLMan = ClusterManager(args)

  if args.cluster:
    if args.cluster in CLMan.clusters:
      checkcluster(CLMan.clusters[args.cluster])
  else:
    for cluster in CLMan.clusters.values():
      checkcluster(cluster)
