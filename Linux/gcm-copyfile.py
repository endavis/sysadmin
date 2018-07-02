#!/usr/bin/env python2
import ConfigParser
import argparse
import os

parser = argparse.ArgumentParser(description='create script to copy file to all hosts')
parser.add_argument('-u', "--username",
                    help="the username to use",
                    default="")
parser.add_argument('-f', "--file", required=True,
                    help="the file to copy",
                    default="")
parser.add_argument('-l', "--location", required=True,
                    help="the location on the destination to copy to",
                    default="")
targs = vars(parser.parse_args())

config = ConfigParser.ConfigParser()
config.read('/home/endavis/src/wk/gcm/gcm.conf')

sshhosts = []

for section in config.sections():
    if config.has_option(section, 'host'):
        group = config.get(section, 'group')
        if 'Linux' in group:
          if 'DAL09' in group or 'WDC04' in group:
            if 'username' in targs and targs['username']:
                sshhosts.append('%s@%s'% (targs['username'], config.get(section, 'host')))

            elif config[section]['user']:
                sshhosts.append('%s@%s'% (config.get(section, 'user'), config.get(section, 'host')))

            else:
                sshhosts.append(config.get(section, 'host'))

tfile = open('copy.sh', 'w')

for host in sshhosts:
  tfile.write('scp %s %s:%s\n' % (targs['file'], host, os.path.join(targs['location'], targs['file'])))

tfile.close()
