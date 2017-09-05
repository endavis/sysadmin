storagetier = {}

storagetier['READHEAVY_TIER'] = '2 IOPs/GB'
storagetier['WRITEHEAVY_TIER'] = '4 IOPs/GB'
storagetier['10_IOPS_PER_GB'] = '10 IOPs/GB'
storagetier['LOW_INTENSITY_TIER'] = '0.25 IOPs/GB'

def convertstoragetoiops(stype):
  return storagetier[stype]
