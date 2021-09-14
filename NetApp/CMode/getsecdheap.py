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

local_tz = 'US/Central'

fromaddress = 'fromaddress'
toaddress = 'toaddress'
mailserver = 'somemailserver'

timezoneoutput = 'US/Central'


def getdestination(cluster):
  """
  get information for a specific cluster
  """
  cmdnode1 = "set d;diag secd echo -node %s-01 -echo-text showLimits" % cluster.name
  cmdnode2 = "set d;diag secd echo -node %s-02 -echo-text showLimits" % cluster.name

  output = cluster.runinteractivecmd(cmdnode1)                                  
  
  for line in output:
    if 'Max Virtual size' in line:
      maxvsize = int(line.split()[-1])
    elif 'Virtual Size' in line:
      vsize = int(line.split()[-1])

  percentage = '{:.2%}'.format(vsize / maxvsize)
 
  body = \
"""
Cluster: %s
Node: %s
Virtual Size: %s
Max Virtual Size: %s
Percentage: %s
""" % (cluster.name, cluster.name + '-01', vsize, maxvsize, percentage)

  output = cluster.runinteractivecmd(cmdnode2)                                  
  
  for line in output:
    if 'Max Virtual size' in line:
      maxvsize = int(line.split()[-1])
    elif 'Virtual Size' in line:
      vsize = int(line.split()[-1])

  percentage = '{:.2%}'.format(vsize / maxvsize)
 
  now = datetime.now()
  date_t = now.strftime('%d/%m/%Y %H:%M')

  body = body + \
"""
Cluster: %s
Node: %s
Virtual Size: %s
Max Virtual Size: %s
Percentage: %s
""" % (cluster.name, cluster.name + '-02', vsize, maxvsize, percentage)

  return body

if __name__ == '__main__':
  args = naparser.parse_args()

  CLMan = ClusterManager(args)

  
  nowtime = datetime.now(timezone(timezoneoutput))
  date_t = nowtime.strftime('%m/%d/%Y %H:%M') + ' ' + timezoneoutput

  msgtext = """
SECD Virtual Memory Update: %s

  """ % date_t

  for cluster in CLMan.clusters.values():
      msgtext = msgtext + '\n' + getdestination(cluster)

  print(msgtext)

  msg = MIMEText(msgtext)

  msg['Subject'] = 'SECD Virtual Memory Update: %s' % date_t
  msg['From'] = fromaddress
  msg['To'] = toaddress

  s = smtplib.SMTP(mailserver)
  s.sendmail(fromaddress, toaddress.split(','), msg.as_string())
  s.quit()


    