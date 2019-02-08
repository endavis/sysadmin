#!/usr/bin/env python
from paramiko import SSHClient, RSAKey
import os
import math
import string
import sys
import argparse
import configparser
import time
import re

naparser = argparse.ArgumentParser()
naparser.add_argument('-c', '--configfile', dest='configfile',
          help='specify a config file (it must exist), if config file is not specified, it defaults to na.ini in the current directory')

def find_config(args):
  """
  find the config file

  defaults to na.ini in the working directory
  """
  configfile = None

  if args.configfile:
    configfile = args.configfile
  else:
    configfile = os.path.join(os.getcwd(), "na.ini")

  if not os.path.join(configfile):
    thelp = naparser.format_usage()
    thelp = thelp + '\n' + "Config file %s does not exist" % configfile
    thelp = thelp + '\n  ' + configfile

    print(thelp)
    sys.exit(1)

  return configfile

class SSH:
  def __init__(self, serverdns, username=None, pw=None, 
               keyfile=None, keyfile_pw=None, logfile=None):
    self.serverdns = serverdns
    self.cname = self.serverdns.split('.')[0]

    if not logfile:
      logname = time.strftime("%d%b%Y")
      self.logfile = open(os.path.join('./logs', '%s-%s.log' % (self.cname, logname)), 'a')
    else:
      self.logfile = logfile

    self.ssh = SSHClient()
    self.ssh.load_system_host_keys()

    self.username = username
    self.pw = pw
    self.pkey_filename = keyfile
    self.pkey_pw = keyfile_pw

    self.pkey = None
    if self.pkey_filename:
      self.pkey = RSAKey.from_private_key_file(self.pkey_filename, password=self.pkey_pw)

    self.chan = None


  def log(self, line):
    """
    write to the log file
    """
    self.logfile.write(line)

  def connect(self):
    if not self.ssh.get_transport() or not self.ssh.get_transport().is_active():
      if self.pkey:
        self.ssh.connect(self.serverdns, username=self.username, pkey=self.pkey)
      else:
        self.ssh.connect(self.serverdns, username=self.username, password=self.pw)

  def runcmd(self, cmd, excludes=None):
    """
    run a command and returns the output
    """
    self.connect()

    if not excludes:
      excludes = []

    excludes.append('\a')
    self.log('%s - %s - %s\n' % (time.strftime("%a %d %b %Y %H:%M:%S %Z"), self.serverdns, cmd))
    output = []
    stdin, stdout, stderr = self.ssh.exec_command(cmd)
    if stderr:
      for line in stderr:
        print(line)
    for line in stdout:
      line = line.rstrip()

      self.log('   %s\n' % line)
      if "Press <space> to page down" in line:
        stdin.write(' ')
        stdin.flush()
      else:
        save = True
        if excludes:
          for exc in excludes:
            if exc in line:
              save = False
              break
        if save:
          output.append(line)

    return output

  def runsudocmd(self, cmd, password):
    """
    run a command through sudo
    """
    output = []
 
    stdin, stdout, stderr = self.ssh.exec_command('sudo -S %s' % cmd, get_pty=True)
    stdin.write('%s\n' % password)
    stdin.flush()
    if stderr:
      for line in stderr:
        print(line)
    for line in stdout:
      line = line.rstrip()

      self.log('   %s\n' % line)
      if "Press <space> to page down" in line:
        stdin.write(' ')
        stdin.flush()
      else:
        save = True
        if save:
          output.append(line)

    return output


  def runinteractivecmd(self, cmd, respondto=' {y|n}:', response='y'):
    """
    run a command that requires a response, also used to see output of a command
    """
    output = []

    self.connect()
    print(cmd)
    self.log('%s - %s - %s\n' % (time.strftime("%a %d %b %Y %H:%M:%S %Z"), self.cname, cmd))
    stdin, stdout, stderr = self.ssh.exec_command(cmd)
    if stderr:
      for line in stderr:
        print(line)
    for line in stdout:
      print(line)
      line = line.rstrip()
      self.log('   %s\n' % line)      
      if respondto in line:
        self.log('sending %s to server' % response)
        print('sending %s to server' % response)
        stdin.write(response)
        stdin.flush()
      else:
        output.append(line)

    return output

class Audit():
  def __init__(self, args):
    self.args = args

    self.clusters = {}

    self.configfile = find_config(args)
    self.cp = configparser.ConfigParser()
    self.cp.read(self.configfile)

  def run(self):
    """
    get all audit logs needed in the config
    """
    for section in self.cp.sections():

      if section == 'Credentials':
        continue

      self.logfile = open('%s.txt' % section, 'w')

      servers = dict(self.cp.items(section))
      keys = servers.keys()
      keys.sort()

      for servernum in keys:
        server = self.cp[section][servernum]
        self.logfile.write('-' * 20 + '    %s    ' % server + '-' * 20 + '\n')
        self.singleserver(server)

  def singleserver(self, server):
    """
    get audit logs for a single server
    """
    sshclient = SSH(server,
                    username = self.cp['Credentials']['username'],
                    pw = self.cp['Credentials']['pw'],
                    keyfile = self.cp['Credentials']['keyfile'],
                    keyfile_pw = self.cp['Credentials']['keyfile_pw'],
                    )

    sshclient.connect()
    self.logfile.write('############# /etc/password #############\n')
    output = sshclient.runsudocmd('cat /etc/passwd', password=sshclient.pw)
    for line in output:
      if '[sudo] password' in line:
        continue
      self.logfile.write(line + '\n')
    self.logfile.write('############# /etc/group #############\n')
    output = sshclient.runsudocmd('cat /etc/group', password=sshclient.pw)
    for line in output:
      if '[sudo] password' in line:
        continue
      self.logfile.write(line + '\n')
    self.logfile.write('############# /etc/sudoers #############\n')
    output = sshclient.runsudocmd('cat /etc/sudoers', password=sshclient.pw)
    for line in output:
      if '[sudo] password' in line:
        continue
      self.logfile.write(line + '\n')
    

if __name__ == "__main__":
    args = naparser.parse_args()

    Audit = Audit(args)
    Audit.run()