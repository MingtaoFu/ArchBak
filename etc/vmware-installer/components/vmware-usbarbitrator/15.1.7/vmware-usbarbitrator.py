"""
Copyright 2010 VMware, Inc.  All rights reserved. -- VMware Confidential

VMware USB Arbitrator component installer.
"""

DEST = LIBDIR/'vmware'

class USBArbitrator(Installer):
   """
   This class contains the installer logic for the USB Arbitrator component.
   """
   def InitializeInstall(self, old, new, upgrade):
      self.AddTarget('File', 'bin/*', DEST/'bin')
      self.SetPermission(DEST/'bin/*', BINARY)

      # Register the init script and link to the appropriate runlevels
      self.RegisterService(name='vmware-USBArbitrator', src='etc/init.d/vmware-USBArbitrator', start=50, stop=8)

   def PreUninstall(self, old, new, upgrade):
      # Stop the USB Arbitrator init script
      script = INITSCRIPTDIR/'vmware-USBArbitrator'
      if script.exists() and self.RunCommand(script, 'stop', ignoreErrors=True).retCode != 0:
            log.Warn(u'Unable to stop USB Arbitrator service.')

      inits = self.LoadInclude('initscript')
      inits.DeconfigureService('vmware-USBArbitrator')


   def PostUninstall(self, old, new, upgrade):
      # If there is a backup LIBDIR/'vmware/lib/vmware-usbarbitrator.old'
      # then restore it, otherwise, remove it.
      orig = BINDIR/'vmware-usbarbitrator'
      backup = LIBDIR/'vmware/lib/vmware-usbarbitrator.old'
      try:
         orig.remove()
      except OSError:
         # Pass if it is already gone
         pass
      if backup.exists():
         backup.copyfile(str(orig))
         orig.chmod(0755)
         backup.remove()


   def PostInstall(self, old, new, upgrade):
      # If an arbitrator already exists and it's not a symlink, back
      # it up and create a symlink to our new ones.  This must be
      # done for co-installs with WS 7.x
      arb = BINDIR/'vmware-usbarbitrator'
      if arb.exists():
         if not arb.islink():
            # Make the destination directory if it doesn't already exist
            dest = path(LIBDIR/'vmware/lib')
            if not dest.exists():
               dest.makedirs()
            # Backup the program (Don't use a path, explicitly convert to a string)
            arb.copyfile(str(LIBDIR/'vmware/lib/vmware-usbarbitrator.old'))
            arb.remove()
         else:
            # Remove the old link
            arb.remove()

      # Now that our space in the BINDIR is clear, install the symlink.
      path(LIBDIR/'vmware/bin/vmware-usbarbitrator').symlink(str(arb))

      inits = self.LoadInclude('initscript')
      inits.ConfigureService('vmware-USBArbitrator',
                             'This services starts and stops the USB Arbitrator.',
                             'localfs', # Start
                             'localfs', # Stop
                             '',
                             '',
                             50,
                             8)

      # Stop the USB Arbitrator init script
      script = INITSCRIPTDIR/'vmware-USBArbitrator'
      if script.exists() and self.RunCommand(script, 'stop', ignoreErrors=True).retCode != 0:
            log.Warn(u'Unable to stop current USB Arbitrator service.  Not fatal.')

      # Start the USB Arbitrator init script
      script = INITSCRIPTDIR/'vmware-USBArbitrator'
      if script.exists() and self.RunCommand(script, 'start', ignoreErrors=True).retCode != 0:
            log.Error(u'Unable to start USB Arbitrator service.')
