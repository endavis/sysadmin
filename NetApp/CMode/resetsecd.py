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

local_tz = 'US/Eastern'

fromaddress = 'fromaddress'
toaddress = 'toaddress'
mailserver = 'mailserver'
fromaddress = 'SECDMemoryStats@wolterskluwer.com'
mailserver = 'bulkmail-int.wkrainier.com'
toaddress = 'eric.davis@wolterskluwer.com'

timezoneoutput = 'US/Eastern'

def checknodeneedsrestart(node, threshhold):
  """
  return true if node is over threshhold
  """
  try:
    percentage = node['secdstats']['Virtual Size'] / node['secdstats']['Max Virtual size']
    if percentage > threshhold:
      return True

  except KeyError:
    pass

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
        output.append('Node %s secd was forced restarted' % node['Node'])
      else:
        output.append('Node %s secd was over the threshhold %s and was restarted' % (node['Node'], threshhold))
      restartnodecmd = 'set d -c off;diag secd restart -node %s' % node['Node']
      output.extend(cluster.runinteractivecmd(restartnodecmd, respondto='This command can take up to 2 minutes to complete.'))

  return output

if __name__ == '__main__':

  naparser.add_argument('-e', '--environment', required=True,
                  help='The environment this script is checking')
  naparser.add_argument('-t', '--threshhold', type=int, default=65,
                  help='The threshhold to restart secd if above')
  naparser.add_argument('-f', '--force', action='store_true',
                  help='Force restart secd with no checking')
  naparser.add_argument('-ar', '--autorestarttime', action="append",
                  help='the time to do an autorestart, in military time. Example: 16:00, can pass multiple times')
  
  args = naparser.parse_args()

  print args.autorestarttime

  nowtime = datetime.now(timezone(timezoneoutput))
  date_t = nowtime.strftime('%m/%d/%Y %H:%M') + ' ' + timezoneoutput
  time = nowtime.strftime('%H:%M')

  for ctime in args.autorestarttime:
    if time == ctime:
      args.force = True

  if args.force:
    subject = 'SECD Automatic Restart for %s at %s' % (args.environment, date_t)
  else:
    subject = 'SECD Threshhold Restart for %s at %s' % (args.environment, date_t)

  output = ["",
            subject,
            "",
            ""]

  CLMan = ClusterManager(args)
  out = []
  for cluster in CLMan.clusters.values():
    out.extend(checknodes(cluster, args.threshhold, args.force))

  if out:
    print('%s: Restart occured' % date_t)
    output.extend(out)
    msgtext = '\n'.join(output)

    print(msgtext)

    msg = MIMEText(msgtext)

    msg['Subject'] = subject
    msg['From'] = fromaddress
    msg['To'] = toaddress

    s = smtplib.SMTP(mailserver)
    s.sendmail(fromaddress, toaddress.split(','), msg.as_string())
    s.quit()
  else:
    print('%s: Nothing to do' % date_t)


    