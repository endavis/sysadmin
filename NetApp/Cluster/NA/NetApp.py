#!/usr/bin/env python3
from paramiko import SSHClient, RSAKey
from .humanize import approximate_size
import os
import math
import string
import sys
import argparse
import configparser

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

BYTE = 1000

NUMBYTES = {}
NUMBYTES['KB'] = float(BYTE)
NUMBYTES['MB'] = NUMBYTES['KB'] * BYTE
NUMBYTES['GB'] = NUMBYTES['MB'] * BYTE
NUMBYTES['TB'] = NUMBYTES['GB'] * BYTE

def convertnetappsize(size):
  ts = size[-2:]
  if ts in NUMBYTES:
    num = size[0:-2]
    num = float(num.strip())
    newsize = num * NUMBYTES[ts]
    return newsize
  else:
    return size

class Volume:
  def __init__(self, name, vserver):
    self.name = name
    self.vserver = vserver
    self.attr = {}

  def sset(self, key, value):
    self.attr[key] = value

class Vserver:
  def __init__(self, name, host):
    self.name = name
    self.host = host
    self.volumes = {}
    self.attr = {}

  def getvolumes(self):
    if not self.volumes:
      cmd = 'vol show -vserver %s -instance' % self.name
      output = self.host.runcmd(cmd, excludes=['Vserver Name', 'There are no entries matching your query.'])
      currentvolume = None
      for line in output:
        if not line:
          continue
        if 'Volume Name' in line:
          currentvolume = line.split(':')[1].strip()
          self.volumes[currentvolume] = Volume(currentvolume, self)
        else:
          line = line.strip()
          tlist = line.split(':')
          key = tlist[0].strip()
          value = tlist[1].strip()
          if 'size' in key or 'Size' in key:
            nvalue = convertnetappsize(value)
            if nvalue != value:
              value = nvalue
          self.volumes[currentvolume].sset(key, value)

  def sset(self, key, value):
    self.attr[key] = value

class NetAppHost:
  def __init__(self, host, username=None, pw=None, keyfile=None, keyfile_pw=None):
    self.host = host

    self.name = None
    self.uuid = None
    self.serialnumber = None
    self.location = None
    self.contact = None

    self.vservers = {}
    self.snapmirrors = []
    self.peers = {}
    self.peersrev = {}

    self.ssh = SSHClient()
    self.ssh.load_system_host_keys()

    self.username = username
    self.pw = pw
    self.pkey_filename = keyfile
    self.pkey_pw = keyfile_pw

    self.pkey = None
    if self.pkey_filename:
      self.pkey = RSAKey.from_private_key_file(self.pkey_filename, password=self.pkey_pw)

    self.getclusterinfo()
    self.getsvms()

  def getclusterinfo(self):
    output = self.runcmd('cluster identity show')
    for line in output:
      if not line:
        continue
      if 'Cluster UUID:' in line:
        self.uuid = line.split(':')[1].strip()
      if 'Cluster Name:' in line:
        self.name = line.split(':')[1].strip()
      if 'Cluster Serial Number:' in line:
        self.serialnumber = line.split(':')[1].strip()
      if 'Cluster Location:' in line:
        tlist = line.split(':')
        if len(tlist) > 1:
          self.location = line.split(':')[1].strip()
      if 'Cluster Contact:' in line:
        tlist = line.split(':')
        if len(tlist) > 1:
          self.contact = line.split(':')[1].strip()

  def getpeers(self):
    output = self.runcmd('vserver peer show-all -instance')
    peer = {}
    for line in output:
      if not line:
        continue
      if 'Local Vserver Name' in line:
        if peer:
          self.peers[peer['Local Vserver Name']] = peer
          self.peersrev[peer['Peer Vserver Name']] = peer
          peer = {}
        local = line.split(':')[1].strip()
        peer['Local Vserver Name'] = local
      elif 'Peer Vserver Name' in line:
        peername = line.split(':')[1].strip()
        peer['Peer Vserver Name'] = peername
      else:
        line = line.strip()
        tlist = line.split(':')
        slist = [x.strip() for x in tlist]
        try:
          peer[slist[0]] = slist[1]
        except IndexError:
          print('The following line was malformed')
          print(line)

  def getsnapmirror(self):
    output = self.runcmd('snapmirror show -instance')
    count = 0
    cursnap = {}
    for line in output:
      if not line:
        continue
      if 'Source Path:' in line:
        if cursnap:
          self.snapmirrors.append(cursnap)
          cursnap = {}
        tlist = line.split(':')
        cursnap['Source Path'] = {'svm':tlist[1].strip(), 'vol':tlist[2].strip()}
      elif 'Destination Path' in line:
        tlist = line.split(':')
        cursnap['Destination Path'] = {'svm':tlist[1].strip(), 'vol':tlist[2].strip()}
      else:
        line = line.strip()
        tlist = line.split(':')
        slist = [x.strip() for x in tlist]
        cursnap[slist[0]] = slist[1]

  def getsvms(self):
    output = self.runcmd('vserver show -instance')
    currentvserver = ''
    lastkey = None
    for line in output:
      if not line:
        lastkey = None
        continue
      if 'Vserver:' in line:
        currentvserver = line.split()[1]
        self.vservers[currentvserver] = Vserver(currentvserver, self)
      else:
        line = line.strip()
        tlist = line.split(':')
        slist = [x.strip() for x in tlist]
        try:
          self.vservers[currentvserver].sset(slist[0], slist[1])
          lastkey = slist[0]
        except IndexError:
          if lastkey and len(slist) == 1:
            if type(self.vservers[currentvserver].attr[lastkey]) == list:
              self.vserver[currentvserver].attr[lastkey].append(slist[0])
            else:
              nvalue = [self.vservers[currentvserver].attr[lastkey], slist[0]]
              self.vservers[currentvserver].sset(lastkey, nvalue)

  def runcmd(self, cmd, excludes=None):
    if not self.ssh.get_transport() or not self.ssh.get_transport().is_active():
      if self.pkey:
        self.ssh.connect(self.host, username=self.username, pkey=self.pkey)
      else:
        self.ssh.connect(self.host, username=self.username, password=self.pw)


    if not excludes:
      excludes = []

    excludes.append('entries were displayed')

    output = []
    stdin, stdout, stderr = self.ssh.exec_command(cmd)
    for line in stdout:
      line = line.rstrip()

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

class NAManager:
  def __init__(self, args):
    self.args = args

    self.netapps = {}

    self.configfile = find_config(args)
    self.cp = configparser.ConfigParser()
    self.cp.read(self.configfile)

    for section in self.cp.sections():

      if section == 'Credentials':
        continue

      self.netapps[section] = NetAppHost(self.cp[section]['host'],
                         username = self.cp['Credentials']['username'],
                         pw = self.cp['Credentials']['pw'],
                         keyfile = self.cp['Credentials']['keyfile'],
                         keyfile_pw = self.cp['Credentials']['keyfile_pw'],
                         )

