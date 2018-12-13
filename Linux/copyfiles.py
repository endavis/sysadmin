#!/usr/bin/env python

import pprint
import os
import re, subprocess, sys, tempfile, thread, time
from threading import Thread
from Queue import Queue

FILES = {}

class rsync_in_parallel(object):
    """Main class for managing parallel rsyncs"""

    def __init__(self, num_threads=10, debug=True):
        """arguments are:
        the user's rsync command,
        the number of threads to spawn for file transfers (default=2),
        and a flag to show debug information (default=False)"""
        self.rsync_cmd = 'rsync -gopvzt'
        self.num_threads = num_threads
        self.debug = debug

        self.queue = Queue()

        for i in range(self.num_threads):
            worker = Thread(target=self._launcher, args=(i,))
            worker.setDaemon(True)
            worker.start()

    def _launcher(self, i):
        """Spawns an rsync process to update/sync a single file"""
        while True:
            tfile = self.queue.get()
            if self.debug:
                print("Thread %s - STARTING: %s\n" % (i, tfile['mirror']))

            cmd = "%s %s %s" % (self.rsync_cmd, tfile['mirror'], tfile['newphys'])
            if self.debug:
                print("Thread %s - CALLING : %s\n" % (i, cmd))
            tstdout = tempfile.NamedTemporaryFile()
            tstderr = tempfile.NamedTemporaryFile()


            start = time.time()

            ret = subprocess.call(cmd, stdout=tstdout, stderr=tstderr, shell=True)
            if ret != 0:
                print("WARN: could not transfer %s, rsync failed with error code=%s; continuing...\n" % (tfile['mirror'], ret))

            end = time.time()

            print("  ----------- START: %s -----------" % tfile['mirror'])
            print "  Thread %s: %s" % (i, tfile['mirror'])
            print "  Started at: %s" % (time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime()))
            print("  -- START stdout:")
            tstdout.seek(0)
            for line in tstdout:
              print("  " + line)
            print("  -- END stdout:")
            print("  -- START stderr:")
            tstderr.seek(0)
            for line in tstderr:
              print("  " + line)
            print("  -- END stderr:")

            tstdout.close()
            tstderr.close()
            print("  Thread %s: %s" % (i, tfile['mirror']))
            print("  Finished at: %s" % (time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime())))
            print("  ----------- FINISH: %s -----------" % tfile['mirror'])
            self.queue.task_done()


    def sync_files(self, filelist):
        """The main entry point to start the sync processes"""

        # create a (synchronized) queue for the threads to access
        for tfile in filelist.values():
          if tfile['mirror']:
            self.queue.put(tfile)
        self.queue.join()

        return



def readfile():
  tfile = open('proddb-files.csv', 'rw')

  tfile.readline()

  files = {}

  for tline in tfile:
    tline = tline.rstrip()
    print(tline)
    if tline:
      tspl = tline.split(',')
      dfname = tspl[0]
      oldphys = tspl[1]
      mirror = tspl[2]
      newphys = tspl[3]

      if dfname:
        FILES[dfname] = {}
        FILES[dfname]['dfname'] = dfname
        FILES[dfname]['oldphys'] = oldphys
        FILES[dfname]['mirror'] = mirror
        FILES[dfname]['newphys'] = newphys

  pprint.pprint(FILES)

def checkmirror():
  print("------------- START: Checking files exist on the mirror -----------------")
  tstr = ''
  for tfile in FILES.values():
    if tfile['mirror']:
      if not os.path.exists(tfile['mirror']):
        tstr = tstr + '  File %s does not exist\n' % tfile['mirror']

  if tstr:
    print(tstr)
  else:
    print('  All files found in mirrors')
  print("------------- END: Checking files exist on the mirror -----------------")

def checkdfname():
  print("------------- START: Checking linked files exist -----------------")
  count = 0
  tstr = ''
  for tfile in FILES.values():
    if not os.path.exists(tfile['dfname']):
      count = count + 1
      tstr = tstr + '  File %s does not exist\n' % tfile['dfname']

  if tstr:
    print(tstr)
    print('  Total files to copy: %s' % count)
  else:
    print('  All files found in /oracle')
  print("------------- END: Checking linked files exist -----------------")

def copyfiles():
    start = time.time()

    print("------------- START: Copying files -----------------")

    r = rsync_in_parallel()
    ret = r.sync_files(FILES)

    end = time.time()
    print("  rsyncs completed in %s seconds" % (end - start))
    print("------------- END: Copying files -----------------")

if __name__ == '__main__':
  readfile()
  checkmirror()
  copyfiles()
  checkdfname()


