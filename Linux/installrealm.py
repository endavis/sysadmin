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
    data.append(ldata)

  ofile.close()
  return data

def updatesshdconfig(domain, groups):
  print('updating sshd config')  
  grouplist = []
  for group in groups:
    grouplist.append(group.replace(' ','^').strip())

  print('Saving a backup of sshd_config to /etc/ssh/sshd_config.realmscript.bak')
  shutil.copyfile('/etc/ssh/sshd_config', '/etc/ssh/sshd_config.realmscript.bak')

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
            allgroups.append('%s@%s' % (group.strip(), domain))

      newline = 'AllowGroups %s\n' % ' '.join(allgroups)
      print('Updating AllowGroups in sshd config')
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

def updatesudoers(domain, groups):
  #%utsadlinuxadmins	ALL=(ALL)	ALL
  print('updating sudoers config')  
  print('Saving a backup of sudoers to sudoers.pbis')
  shutil.copyfile('/etc/sudoers', '/etc/sudoers.activedirectory')

  tmpfilepath = '/root/tmp/testsudo'

  if os.path.exists('/etc/sudoers.d'):
    nfile = open(tmpfilepath, 'w')
    for group in groups:
      groupname = '%s@%s' % (group, domain.lower())
      print('Adding group %s to sudo' % groupname)
      nfile.write('%%%s\tALL=(ALL)\tALL\n' % groupname)

    nfile.close()

  status, output = runcommand('visudo -c -f %s' % tmpfilepath, test=False, exit=False)

  if status != 0:
    print('%s failed sudoers check, is not valid. Please check syntax')
  else:
    print('Copying sudoers file into /etc/sudoers.d')
    shutil.copyfile(tmpfilepath, '/etc/sudoers.d/activedirectorysudoers')

def getdomain():
  status, output = runcommand('realm list')
  domain = ''
  if status == 0:
    olist = output.split('\n')
    if olist:
      for line in olist:
        line = line.strip()
        if 'domain-name' in line:
          domain = line.split(':')
          domain = domain[-1]
          domain = domain.strip()

  return domain

def updaterealmconfig(domain):
  """
  update the realm config
  """
  print('updating realm config')
  print('Saving a backup of sssd config to /etc/sssd/sssd.conf.realmscript.bak')
  shutil.copyfile('/etc/sssd/sssd.conf', '/etc/sssd/sssd.conf.realmscript.bak')  

  sssdconfig = readfile('/etc/sssd/sssd.conf')
  newdata = []
  hasdefaultsuffix = any('default_domain_suffix' in line for line in sssdconfig)
  hasoverridehomedir = any('override_homedir' in line for line in sssdconfig)
  print('hasdefaultsuffix: %s' % hasdefaultsuffix)
  print('hasoverridehomedir: %s' % hasoverridehomedir)
  for line in sssdconfig:
    if 'services = ' in line:
      newdata.append(line + '\n')
      if not hasdefaultsuffix:
        print('Adding default domain suffix')
        newdata.append('default_domain_suffix = %s\n' % domain.lower())
    elif 'fallback_homedir' in line:
      print('Updating fallback_homedir')
      newdata.append('fallback_homedir = /home/%d/%u\n')
      if not hasoverridehomedir:
        print('Adding override_homedir')
        newdata.append('override_homedir = /home/%d/%u\n')
    else:
      newdata.append(line + '\n')

  print('Saving new sssd config')
  sssdconfig = open('/etc/sssd/sssd.conf', 'w')
  for line in newdata:
    sssdconfig.write(line)
  sssdconfig.close()
  runcommand('chmod 600 /etc/sssd/sssd.conf')
  runcommand('chown root:root /etc/sssd/sssd.conf')

def updatelogingroups(groups):
  print('updating login groups')
  print('denying all users')
  runcommand('realm deny --all')

  for group in groups:
    groupname = '%s@%s' % (group, args.domain.lower())
    print('adding group %s' % groupname)
    runcommand('realm permit -g %s' % groupname)


def main():
  print('Checking if realm is installed')
  status, output = runcommand('/usr/sbin/realm list', test=False, exit=False)

  if status != 0:
    print('Installing realm')

    runcommand("sudo yum -y install sssd realmd oddjob oddjob-mkhomedir adcli samba-common samba-common-tools krb5-workstation openldap-clients policycoreutils-python")


  print('Checking if this server is joined to a domain')
  domain = getdomain()

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
    runcommand('echo %s | realm join --user=%s %s' % (adminpw, args.adminaccount, args.domain))


  print("Configuring sssd")  
  updaterealmconfig(args.domain)

  print ('restarting sssd')
  runcommand('systemctl restart sssd')
  
  updatelogingroups(args.groups)

  # set ssh groups
  updatesshdconfig(args.domain, args.groups)
  runcommand('service sshd restart')

  # update sudoers
  updatesudoers(args.domain, args.groups)

  runcommand('service sshd status')
  runcommand('service sssd status')
  runcommand('realm list')
  runcommand('cat /etc/sssd/sssd.conf')  

if __name__ == "__main__":
  main()

