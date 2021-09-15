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

CSVFILE_FO = None

def getheapstats(cluster, command):
  """
  get the secd heap data
  """
  output = cluster.runinteractivecmd(command)
  
  for line in output:
    if 'Max Virtual size' in line:
      maxvsize = int(line.split()[-1])
    elif 'Virtual Size' in line:
      vsize = int(line.split()[-1])

  percentage = vsize / maxvsize

  return vsize, maxvsize, percentage

def getdestination(cluster, date_t):
  """
  get information for a specific cluster
  """
  cmdnode1 = "set d;diag secd echo -node %s-01 -echo-text showLimits" % cluster.name
  cmdnode2 = "set d;diag secd echo -node %s-02 -echo-text showLimits" % cluster.name

  node1vsize, node1maxvsize, node1percentage = getheapstats(cluster, cmdnode1)
  node2vsize, node2maxvsize, node2percentage = getheapstats(cluster, cmdnode2)                                
   
  node1data = "%s,%s,%s,%s,%s,%s\n" % (date_t, cluster.name, cluster.name + '-01', node1vsize, node1maxvsize, node1percentage)
  node2data = "%s,%s,%s,%s,%s,%s\n" % (date_t, cluster.name, cluster.name + '-02', node2vsize, node2maxvsize, node2percentage)

  CSVFILE_FO.write(node1data)
  CSVFILE_FO.write(node2data)


if __name__ == '__main__':

  naparser.add_argument('-csv', '--csvfile',
                  help='The csv file to write to')
  args = naparser.parse_args()

  CLMan = ClusterManager(args)

  now = datetime.now()
  date_t = now.strftime('%m/%d/%Y %H:%M:%S')

  CSVFILE_FO = open(args.csvfile, "a")

  for cluster in CLMan.clusters.values():
      getdestination(cluster, date_t)

  CSVFILE_FO.close()
