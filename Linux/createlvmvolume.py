#!/bin/env python
"""
parted /dev/sdb --script -- mkpart primary 0% 100%
parted -s /dev/sdb set 1 lvm on

pvcreate /dev/sdb1
vgcreate vg_two_redo_01 /dev/sdb1
lvcreate -l 98G -n lv_redo_01 two_redo_01
mkfs -t ext4 /dev/mapper/two_redo_01-lv_redo_01
mkdir /mnt/redo_01
echo "/dev/mapper/two_redo_01-lv_redo_01 /mnt/redo_01                 ext4    defaults,noatime        1 2" >> /etc/fstab
mount /mnt/redo_01

echo "- - -" > /sys/class/scsi_host/hosth/scan
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import argparse
import subprocess
import sys
import time

try:
  raw_input
except:
  raw_input = input

naparser = argparse.ArgumentParser()
naparser.add_argument('-m', '--mountpoint', required=True,
        help='the mountpoint of the new volume')
naparser.add_argument('-n', '--name', required=True,
                help='the lvm name, the volume group name will be set to vg_<name>, and the logical volume will be set to lg_<name>')
naparser.add_argument('-d', '--device', required=True,
                help='The device to use')
naparser.add_argument('-t', '--test', action='store_true',
                help='show actions do be taken but do not execute them')

args = naparser.parse_args()

def runcommand(command):
  print("Running command: '%s'" % command)

  p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
  (output, err) = p.communicate()

  p_status = p.wait()
  print("Command output : ", output.rstrip())
  if err:
    print("Command error  : ", err)
  print("Command status : ", p_status)

  if p_status != 0:
    print("Something went wrong, exiting, please check commands")
    sys.exit(1)

  print("")
  time.sleep(2)

def main():
  device = args.device

  volumegroup = "vg_" + args.name
  logicalvolume = "lv_" + args.name

  mountpoint = args.mountpoint

  yesno = raw_input("""The following parameters will be used
  device              : %s
  volume group name   : %s
  logical volume name : %s
  mount point         : %s
Are these correct? (Y/N)\n""" % (device, volumegroup, logicalvolume, mountpoint))

  if yesno.lower() == "n":
    print("Exiting")
    sys.exit(1)


  newpart = device + "1"
  mapperdev = "/dev/mapper/%s-%s" % (volumegroup, logicalvolume)

  cmdcreatelabel = "parted %s --script -- mklabel msdos" % device
  cmdcreatepart = "parted %s --script -- mkpart primary 0%% 100%%" % device
  cmdsetlvm = "parted -s %s set 1 lvm on" % newpart
#  cmdcreatepartlabel = "parted %s --script -- mklabel gpt" % newpart

  cmdpvcreate = "pvcreate %s" % device
  cmdvgcreate = "vgcreate %s %s" % (volumegroup, device)
  cmdlvcreate = "lvcreate -l 100%%FREE -n %s %s" % (logicalvolume, volumegroup)
  cmdmkfs = "mkfs -t ext4 %s" % mapperdev
  fstabline = "%s %s                 ext4    defaults,noatime        1 2\n" % (mapperdev, mountpoint)

  mountcmd = "mount %s" % mountpoint


  print("The following cmds and actions will be taken")
  #print("Command : %s" % cmdcreatelabel
  #print("Command : %s" % cmdcreatepart
  #print("Command : %s" % cmdsetlvm
  print("Command : %s" % cmdpvcreate)
  print("Command : %s" % cmdvgcreate)
  print("Command : %s" % cmdlvcreate)
  print("Command : %s" % cmdmkfs)
  print("Action  : Create directory %s" % mountpoint)
  print("Action  : Add line '%s' to /etc/fstab" % fstabline)
  print("Command : %s" % mountcmd)
  print("")

  if not args.test:
    #runcommand(cmdcreatelabel)
    #runcommand(cmdcreatepart)
    #runcommand(cmdsetlvm)
    runcommand(cmdpvcreate)
    runcommand(cmdvgcreate)
    runcommand(cmdlvcreate)
    runcommand(cmdmkfs)

    os.makedirs(mountpoint)

    fstab = open("/etc/fstab", "a")
    fstab.write(fstabline)
    fstab.close()

    runcommand(mountcmd)


if __name__ == "__main__":
  main()

