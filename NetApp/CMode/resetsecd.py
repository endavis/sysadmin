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
mailserver = 'mailserver'

timezoneoutput = 'US/Central'

def checknodeneedsrestart(node, threshhold):
  """
  return true if node is over threshhold
  """
  percentage = node['secdstats']['Virtual Size'] / node['secdstats']['Max Virtual size']
  if percentage > threshhold:
    return True

  return False

def checknodes(cluster, threshhold, force):
  """
  get information for a specific cluster
  """
  cluster.getsecdstats()
  output = []

  for node in cluster.nodes.values():
    if checknodeneedsrestart(node, threshhold) or force:
      output.append('--------------------------------------------------')
      if force:
        output.append('Node %s secd was forced reloaded' % node['Node'])
      else:
        output.append('Node %s secd was over the threshhold %s and was restarted' % (node['Node'], threshhold))
      resetnodecmd = 'set d -c off;diag secd restart -node %s' % node['Node']
      output.extend(cluster.runinteractivecmd(resetnodecmd, respondto='This command can take up to 2 minutes to complete.'))

  return output

if __name__ == '__main__':

  naparser.add_argument('-e', '--environment', required=True,
                  help='The environment this script is checking')
  naparser.add_argument('-t', '--threshhold', type=int, default=65,
                  help='The threshhold to restart secd if above')
  naparser.add_argument('-f', '--force', action='store_true',
                  help='Force restart secd with no checking')
  naparser.add_argument('-ar', '--autoresettime', default='',
                  help='the time to do an autoreset, in military time. Example: 16:00')
  
  args = naparser.parse_args()

  nowtime = datetime.now(timezone(timezoneoutput))
  date_t = nowtime.strftime('%m/%d/%Y %H:%M') + ' ' + timezoneoutput
  time = nowtime.strftime('%H:%M')
  
  if time == args.autoresettime:
    args.force = True

  CLMan = ClusterManager(args)

  msgtext = """
SECD Reset for %s at %s

  """ % (args.environment, date_t)

  for cluster in CLMan.clusters.values():
      output = checknodes(cluster, args.threshhold, args.force)

  print(output)
  
  if output:
    msgtext = '\n'.join(output)

    print(msgtext)

    msg = MIMEText(msgtext)

    msg['Subject'] = 'SECD Reset for %s: %s' % (args.environment, date_t)
    msg['From'] = fromaddress
    msg['To'] = toaddress

    s = smtplib.SMTP(mailserver)
    s.sendmail(fromaddress, toaddress.split(','), msg.as_string())
    s.quit()


    