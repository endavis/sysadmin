#!/bin/env python
import argparse
import os
import subprocess
import time
import sys
import shutil

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--directory', required=True,
                help='The directory to tar all children')

def getchildsubdirectories(a_dir):
    return [name for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]

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

def tardirectory(directory):
  """
  directory will be a dictionary
   'parent'
   'dir'
  """
  print 'Changing to directory %s' % directory['parent']
  os.chdir(directory['parent'])
  # tar zcvf 20180209.tgz 20180209
  cmd = 'tar zcvf %s.tgz %s' % (directory['dir'], directory['dir'])
  runcommand(cmd)
  return os.path.join(directory['parent'], "%s.tgz" % directory['dir'])

def removedirectory(directory):
  """
  remove a directory
  """
  shutil.rmtree(directory)

def main():
  today = time.strftime('%Y%m%d', time.localtime())
  args = parser.parse_args()
  parentsyslogdir = args.directory
  children = getchildsubdirectories(parentsyslogdir)
  print 'getting children for %s' % parentsyslogdir
  for i in children:
    fullpath = os.path.join(parentsyslogdir, i)
    print 'checking directory %s' % fullpath
    newchildren = getchildsubdirectories(fullpath)
    for i2 in newchildren:
      if i2 == today:
        print 'skipping directory %s' % i2
        continue
      newfullpath = os.path.join(fullpath, i2)
      print 'Tarring directory %s' % (newfullpath)
      tarfile = tardirectory({'parent':fullpath, 'dir':i2})
      if os.path.exists(tarfile) and os.path.getsize(tarfile) > 0:
        print 'tarfile %s exists and its size is > 0' % tarfile
        print 'removing directory %s' % (newfullpath)
        removedirectory(newfullpath)
      else:
        print 'Could not remove directory: %s' % newfullpath
        print 'something is wrong with the tarfile %s' % tarfile


if __name__ == "__main__":
  main()
