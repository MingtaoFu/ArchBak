"""
Copyright 2012 VMware, Inc.  All rights reserved. -- VMware Confidential

vProbe component installer.
"""
DEST = LIBDIR/'vmware'
class Vprobe(Installer):
   def InitializeInstall(self, old, new, upgrade):
      self.AddTarget('File', 'lib/bin/*', DEST/'bin')
      self.AddTarget('File', 'bin/*', BINDIR)

      self.SetPermission(DEST/'*', BINARY)
      self.SetPermission(BINDIR/'*', BINARY)
