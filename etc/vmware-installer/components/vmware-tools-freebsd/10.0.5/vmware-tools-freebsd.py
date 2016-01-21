#
# Copyright 2009 VMware, Inc.  All rights reserved. -- VMware Confidential
#

"""
VMware Tools ISO Component.

This is the VMIS template component file for the freebsd Tools ISO, where
freebsd will be replaced by the name of the specific iso (ie: linux,
windows, freebsd...)
"""
DEST = LIBDIR/'vmware/isoimages'

class ToolsISOfreebsd(Installer):
   def InitializeInstall(self, old, new, upgrade):
      self.AddTarget('File', 'freebsd.iso', DEST/'freebsd.iso')
      self.AddTarget('File', 'freebsd.iso.sig', DEST/'freebsd.iso.sig')
