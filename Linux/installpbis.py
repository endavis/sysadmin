#!/bin/env python
"""

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import argparse
import subprocess
import sys
import time
import shutil
from getpass import getpass

if not os.geteuid() == 0:
    sys.exit("\nOnly root can run this script\n")

try:
  raw_input
except:
  raw_input = input

naparser = argparse.ArgumentParser()
naparser.add_argument('-fd', '--domain', required=True,
                help='the full domain to connect to, example: domain.net')
naparser.add_argument('-sd', '--shortdomain', required=True,
                help='the short version of the domain, example: domain')
naparser.add_argument('-a', '--adminaccount', required=True,
                help='The admin account to use')
naparser.add_argument('-g', '--groups', action='append',
                help='groups to add as ssh and sudo users')
naparser.add_argument('-ui', '--userignore', action='append',
                help='users to ignore in active directory')
naparser.add_argument('-gi', '--groupignore', action='append',
                help='groups to ignore in active directory')

args = naparser.parse_args()

def runcommand(command, test=False, exit=True):
  print("Running command: '%s'" % command)

  if not test:
    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()

    p_status = p.wait()
    print("Command output : ", output.rstrip())
    if err:
      print("Command error  : ", err)
    print("Command status : ", p_status)

    if p_status != 0:
      print("Something went wrong, please check commands")
      if exit:
        sys.exit(1)

    print("")
    time.sleep(2)
    return p_status, output

  return -500, ''

def readfile(nfile):
  """
  read a file by line, strip the line, and add it to an list
  """
  data = []
  ofile = open(nfile)
  for line in ofile:
    ldata = line.strip()
    if ldata:
      data.append(ldata)

  ofile.close()
  return data

def updateignorefile(filename, data):
  fdata = readfile(filename)

  for item in data:
    if item not in fdata:
      print('Adding %s to %s' % (item, filename))
      fdata.append(item)
    else:
      print('%s exists in %s' % (item, filename))
  
  nfile = open(filename, 'w')
  for item in fdata:
    nfile.write('%s\n' % item)
  nfile.close()

def updatesshdconfig(groups):
  grouplist = []
  for group in groups:
    grouplist.append(group.replace(' ','^').strip())

  print('Saving a backup of sshd_config to sshd_config.pbis')
  shutil.copyfile('/etc/ssh/sshd_config', '/etc/ssh/sshd_config.pbis')

  sshconfig = open('/etc/ssh/sshd_config', 'r')
  newdata = []
  allowgroupsfound = None
  authenticationline = None
  for line in sshconfig:
    if '# Authentication:' == line.strip():
      newdata.append(line)
      authenticationline = newdata.index(line)
    elif 'AllowGroups' in line:
      line = line.strip()
      allgroups = line.split(' ')
      
      del allgroups[0]

      for group in grouplist:
          if group not in allgroups:
            allgroups.append(group.strip())

      newline = 'AllowGroups %s\n' % ' '.join(allgroups)
      print('Update AllowGroups in sshd config')
      print(newline)

      newdata.append(newline)
      allowgroupsfound = newdata.index(newline)

    else:
      newdata.append(line)

  sshconfig.close()

  if not allowgroupsfound:
    print('Adding AllowGroups to sshd config')
    newline = 'AllowGroups %s\n' % ' '.join(grouplist)
    newdata.insert(authenticationline + 1, newline)

  print('Saving new ssh config')
  sshconfig = open('/etc/ssh/sshd_config', 'w')
  for line in newdata:
    sshconfig.write(line)
  sshconfig.close()

def updatesudoers(groups):
  #%utsadlinuxadmins	ALL=(ALL)	ALL
  print('Saving a backup of sudoers to sudoers.pbis')
  shutil.copyfile('/etc/sudoers', '/etc/sudoers.pbis')

  tmpfilepath = '/root/tmp/testsudo'

  if os.path.exists('/etc/sudoers.d'):
    nfile = open(tmpfilepath, 'w')
    for group in groups:
      nfile.write('%%%s\tALL=(ALL)\tALL\n' % group)

  nfile.close()

  status, output = runcommand('visudo -c -f %s' % tmpfilepath, test=False, exit=False)

  if status != 0:
    print('%s failed sudoers check, is not valid. Please check syntax')
  else:
    print('Copying sudoers file into /etc/sudoers.d')
    shutil.copyfile(tmpfilepath, '/etc/sudoers.d/pbissudoers')

def main():
  print('Checking if PBIS is already installed')
  status, output = runcommand('/opt/pbis/bin/config --dump | grep -i UserDomainPrefix', test=False, exit=False)

  if status != 0:
    print('Installing PBIS')

    try:
      os.mkdir('/root/tmp')
    except OSError:
      pass

    os.chdir('/root/tmp')

    print("Adding GPG key for PBIS repo")
    runcommand("rpm --import http://repo.pbis.beyondtrust.com/yum/RPM-GPG-KEY-pbis")

    print("Download PBIS repo information")
    runcommand(" wget -O /etc/yum.repos.d/pbiso.repo http://repo.pbis.beyondtrust.com/yum/pbiso.repo")
    print("Installing PBIS")
    runcommand("sudo yum clean all")
    runcommand("sudo yum -y install pbis-open")


  print('Checking if this server is joined to a domain')
  status, output = runcommand('/opt/pbis/bin/domainjoin-cli query')
  domain = ''
  if status == 0:
    for line in output.split('\n'):
      line = line.strip()
      if 'Domain =' in line:
        domain = line.split('=')
        print(domain)
        domain = domain[1]
        domain = domain.strip()
  
  print('In Domain: %s' % domain)
  alreadyindomain = False
  if domain:
    if domain.lower() != args.domain.lower():
      print('This server is already joined to domain %s' % domain)
      print('Please remove this server from domain %s' % domain)
      sys.exit()
    
    if domain.lower() == args.domain.lower():
      print('This server is already joined to domain %s' % args.domain)
      alreadyindomain = True


  if not alreadyindomain:   
    print("Joining domain %s" % args.domain)
    adminpw = getpass(prompt="Please enter the password for %s: " % args.adminaccount)
    runcommand('/opt/pbis/bin/domainjoin-cli join %s %s %s' % (args.domain, args.adminaccount, adminpw))

  print("Configuring PBIS")  
  runcommand('/opt/pbis/bin/config UserDomainPrefix %s' % args.shortdomain)
  runcommand('/opt/pbis/bin/config AssumeDefaultDomain true')
  runcommand('/opt/pbis/bin/config LoginShellTemplate /bin/bash')
  runcommand('/opt/pbis/bin/config HomeDirTemplate %H/%D/%U')


  grouplist = ""
  for group in args.groups:
    ngroup = "\"%s\\%s\"" % (args.shortdomain, group)
    grouplist +=  " " + ngroup
  runcommand('/opt/pbis/bin/config RequireMembershipOf %s' % grouplist)

  if args.userignore:
    updateignorefile('/etc/pbis/user-ignore', args.userignore)
  
  if args.groupignore:
    updateignorefile('/etc/pbis/group-ignore', args.groupignore)  

  # set ssh groups
  updatesshdconfig(args.groups)

  # update sudoers
  updatesudoers(args.groups)

if __name__ == "__main__":
  main()

