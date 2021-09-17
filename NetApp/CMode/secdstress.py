#/usr/bin/env python3
from __future__ import division
from Cluster import ClusterManager, naparser
import sys
import os
import pprint
from pytz import timezone
from email.mime.text import MIMEText
import smtplib
from datetime import datetime
import time

"""
diag secd authentication get-dc-info -vserver svm_ZUSNCLTELFST011 -node ZUSNCLTELFST011-01
diag secd connections test -vserver svm_ZUSNCLTELFST011 -node ZUSNCLTELFST011-01
cifs domain discovered-servers reset
"""
def stressnode(cluster, node2stress, interval, othernode):
  """
  stress the node
  """
  svmname = 'svm_%s' % cluster.name
  node1cmd1 = 'set d -c off;diag secd authentication get-dc-info -vserver %s -node %s' % (svmname, node2stress)
  node1cmd2 = 'set d -c off;diag secd connections test -vserver %s -node %s' % (svmname, node2stress)

  node2cmd1 = 'set d -c off;diag secd authentication get-dc-info -vserver %s -node %s' % (svmname, othernode)
  node2cmd2 = 'set d -c off;diag secd connections test -vserver %s -node %s' % (svmname, othernode)

  discovercmd = 'cifs domain discovered-servers reset'

  now = datetime.now()
  date_t = now.strftime('%m/%d/%Y %H:%M:%S')

  while True:
    print('---------------------------------------')
    print(date_t)
    print("Running cmd: %s" % node1cmd1)
    output = cluster.runcmd(node1cmd1)
    print('\n'.join(output))
    
    print("Running cmd: %s" % node1cmd2)
    output = cluster.runcmd(node1cmd2)
    print('\n'.join(output))

    print("Running cmd: %s" % node2cmd1)
    output = cluster.runcmd(node2cmd1)
    print('\n'.join(output))
    
    print("Running cmd: %s" % node2cmd2)
    output = cluster.runcmd(node2cmd2)
    print('\n'.join(output))

    print("Running cmd: %s" % discovercmd)
    output = cluster.runcmd(discovercmd)
    print('\n'.join(output))

    output4 = cluster.runcmd("set d;diag secd echo -echo-text showLimits -node %s" % node2stress)
    print('stats after runnning for node: %s' % othernode )
    print('\n'.join(output4))

    output5 = cluster.runcmd("set d;diag secd echo -echo-text showLimits -node %s" % othernode)
    print('stats after runnning for node: %s' % othernode )
    print('\n'.join(output5))

    time.sleep(interval)

  
if __name__ == '__main__':
  naparser.add_argument('-i', '--interval', type=int, default=5,
                  help='The interval (in seconds) to stress secd')
  args = naparser.parse_args()

  CLMan = ClusterManager(args)

  now = datetime.now()
  date_t = now.strftime('%m/%d/%Y %H:%M:%S')

  node2stress = 'ZUSNCLTELFST010-01'
  othernode = 'ZUSNCLTELFST010-02'

  for cluster in CLMan.clusters.values():
    if node2stress in cluster.nodes:
      stressnode(cluster, node2stress, args.interval, othernode)


