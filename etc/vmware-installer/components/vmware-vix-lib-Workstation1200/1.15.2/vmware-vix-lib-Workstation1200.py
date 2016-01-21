"""
Copyright 2007 VMware, Inc.  All rights reserved. -- VMware Confidential

VIX Workstation1200 library component installer.
"""
DEST = LIBDIR/'vmware-vix'

class VIXLibWorkstation1200(Installer):
   def InitializeInstall(self, old, new, upgrade):
      self.AddTarget('File', 'lib/*', DEST)
