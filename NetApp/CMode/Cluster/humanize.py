'''Convert file sizes to human-readable form.

Available functions:
approximate_size(size, a_kilobyte_is_1024_bytes)
    takes a file size and returns a human-readable string

Examples:
>>> approximate_size(1024)
'1.0 KiB'
>>> approximate_size(1000, False)
'1.0 KB'

'''

SUFFIXES = {1000: ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
            1024: ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']}

def approximate_size(size, a_kilobyte_is_1024_bytes=True, newsuffix=None, withsuffix=True):
  '''Convert a file size to human-readable form.

  Keyword arguments:
  size -- file size in bytes
  a_kilobyte_is_1024_bytes -- if True (default), use multiples of 1024
                              if False, use multiples of 1000

  Returns: string

  '''
  if size < 0:
      raise ValueError('number must be non-negative')

  if newsuffix:
    return approximate_size_specific(size, newsuffix, withsuffix)

  multiple = 1024 if a_kilobyte_is_1024_bytes else 1000
  for suffix in SUFFIXES[multiple]:
      size /= multiple
      if size < multiple:
        if withsuffix:
          return '{0:.2f} {1}'.format(size, suffix)
        else:
          return size

  raise ValueError('number too large')

def approximate_size_specific(size, newsuffix, withsuffix=True):
  """
  converts a size in bytes to a specific suffix (like GB, TB, TiB)
  """
  for multiple in SUFFIXES:
    for suffix in SUFFIXES[multiple]:
      if suffix.lower() == newsuffix.lower():
        power = SUFFIXES[multiple].index(suffix)
        newsizeint = float(size) / (multiple ** float(power+1))
        if withsuffix:
          return '{0:.2f} {1}'.format(newsizeint, suffix)
        else:
          return newsizeint

  return -1

def convert_size(dsize, newsuffix, withsuffix=True):
  '''Convert a file size like 8TB to another size

  Keyword arguments:
  size -- file size in bytes
  newsuffix -- the suffix to change it to
  withsuffix -- return size with new suffix, otherwise returns just
            the number

  Returns: a new size

  '''
  newsize = 0
  foundmult = 0
  power = 0
  foundsuffix = 0

  for multiple in SUFFIXES:
    for suffix in SUFFIXES[multiple]:
      if suffix in dsize:
        foundmult = multiple
        foundsuffix = suffix
        power = SUFFIXES[multiple].index(suffix) + 1
        size = dsize.replace(foundsuffix, "").strip()
        size = float(size)
        newsize = size * (foundmult ** power)

  newsizes = approximate_size_specific(newsize, newsuffix)

  if withsuffix:
    return newsizes

  else:
    return float(newsizes.replace(newsuffix, ""))

  #if newsize > 0:
    #print "Old Size: %s" % dsize
    #print "Num Size: %d" % size
    #print "New Size: %d" % newsize
    #print "New Size: %s" % newsizes
    #print "Converted back: %s" % approximate_size(newsize, True if foundmult == 1024 else False)


if __name__ == '__main__':
    print(approximate_size(1000000000000, False))
    print(approximate_size(1000000000000))

# Copyright (c) 2009, Mark Pilgrim, All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
