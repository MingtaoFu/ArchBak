"""
Copyright 2008 VMware, Inc.  All rights reserved. -- VMware Confidential

VMware Workstation component installer.
"""
DEST = LIBDIR/'vmware'
conf = DEST/'setup/vmware-config'
LICENSETOOL=BINDIR/'vmware-license-enter.sh'

PRODUCT = 'VMware Workstation'
LICENSEVERSION = '12.0'

LIMITSFILE = Destination('/etc/security/limits.conf')
NOFILE_MINIMUM = 4096
PAMLOGINFILE = Destination('/etc/pam.d/login')

vmwareSentinel = '# Automatically generated by the VMware Installer - DO NOT REMOVE\n'
pamLoginLine = 'session    required   pam_limits.so\n'

class Workstation(Installer):
   def PreTransactionInstall(self, old, new, upgrade):
      # Include update module
      globals()['update'] = self.LoadInclude('update')

      iconImages = ['share/icons/hicolor/%dx%d/apps/vmware-workstation.png' % \
                       (size, size) for size in [16, 32, 48]]

      gui.SetBannerImage('files/banner.png')
      gui.SetIconImages(iconImages)
      gui.SetHeaderImage('share/icons/hicolor/48x48/apps/vmware-workstation.png')

   def PreTransactionUninstall(self, old, new, upgrade):
      # Include update module
      globals()['update'] = self.LoadInclude('update')

   def InitializeQuestions(self, old, new, upgrade):

      self.AddQuestion('TextEntry',
                       key='serialNumber',
                       text='',
                       header='Enter license key.',
                       footer='(optional) You can enter this information later.',
                       default='',
                       required=True,
                       level='REGULAR')

      # NOFILE hardlimit
      nofileHL = self.GetAnswer('nofileHardLimit')
      if nofileHL:
         qlevel = 'CUSTOM'
      else:
         qlevel = 'REGULAR'
      try:
         self.hardLimit = self.RunCommand('/bin/sh', '-c', 'ulimit -H -n').stdout
         self.hardLimit = self.hardLimit.strip()
         self.hardLimit = int(self.hardLimit)
         if self.hardLimit < NOFILE_MINIMUM:
            log.Debug('Hard limit is %d, adding question.', self.hardLimit)
            self.AddQuestion('NumericEntry',
                             key='nofileHardLimit',
                             text='Insufficient file descriptors can cause virtual machines to '
                                  'crash when using snapshots.  The installer has detected that '
                                  'your hard limit for open files is %d, which is lower than VMware '
                                  'Workstation may require.  Please enter a new limit.' % self.hardLimit,
                             min=1024,
                             max=65536,
                             required=False, default=NOFILE_MINIMUM, level=qlevel)
      except ValueError:
         # Log this, but move on.  Not a fatal error.
         log.Error('Hard limit returned non-integer value: %s', self.hardLimit)

   def InitializeInstall(self, old, new, upgrade):
      self.AddTarget('File', 'bin/*', BINDIR)
      self.AddTarget('File', 'man/*', MANDIR)

      self.AddTarget('File', 'share/icons/*', DATADIR/'icons')

      if self.GetConfig('installShortcuts', component='vmware-installer') != 'no':
         self.AddTarget('File', 'share/applications/*', DATADIR/'applications')
         self.AddTarget('File', 'share/appdata/*', DATADIR/'appdata')

      self.AddTarget('File', 'lib/*', DEST)
      self.AddTarget('File', 'doc/*', DOCDIR/'vmware-workstation')
      self.AddTarget('File', 'etc/*', SYSCONFDIR)

      # Symlink all binaries to appLoader.
      for i in ('vmware', 'vmware-tray'):
        self.AddTarget('Link', DEST/'bin/appLoader', DEST/'bin'/i)

      self.SetPermission(DEST/'bin/*', BINARY)

      # Ubuntu 10.04 requires additional .desktop files in /usr/local/share/applications
      # If GNOME or Ubuntu is going this way, rather than just add these links for
      # Ubuntu 10.04, always add them for future-proofing.

      # Some linux distributions use yet another standard for DE metadata, requiring
      # .appdata.xml files in order for WS to be usable via the DE app launcher.
      # Like the .desktop files, just install them along with the rest for futureproofing.
      if self.GetConfig('installShortcuts', component='vmware-installer') != 'no':
         self.AddTarget('Link', DATADIR/'applications/vmware-workstation.desktop',
                        PREFIX/'local/share/applications/vmware-workstation.desktop')
         self.AddTarget('Link', DATADIR/'appdata/vmware-workstation.appdata.xml',
                        PREFIX/'local/share/appdata/vmware-workstation.appdata.xml')


   def PreUninstall(self, old, new, upgrade):
      self.RunCommand(conf, '-d', 'product.version')
      self.RunCommand(conf, '-d', 'workstation.product.version')
      self.RunCommand(conf, '-d', 'vix.config.version')

      # Stop our init script for uninstallation
      script = INITSCRIPTDIR/'vmware'
      if INITSCRIPTDIR and script.exists():
         self.RunCommand(script, 'stop', ignoreErrors=True)


   def PostInstall(self, old, new, upgrade):
      # Used by VIX to locate correct provider.
      self.RunCommand(conf, '-s', 'product.version', self.GetManifestValue('version'))
      self.RunCommand(conf, '-s', 'workstation.product.version', self.GetManifestValue('version'))
      self.RunCommand(conf, '-s', 'product.name', PRODUCT)
      self.RunCommand(conf, '-s', 'vix.config.version', 1)

      if self.GetConfig('installShortcuts', component='vmware-installer') != 'no':
         launcher = DATADIR/'applications/vmware-workstation.desktop'
         binary = BINDIR/'vmware'
         self.RunCommand('sed', '-e', 's,@@BINARY@@,%s,g' % binary, '-i', launcher)

      update.UpdateIconCache(self, DATADIR)
      update.UpdateMIME(self, DATADIR)

      # Update hard limit for the number of open files.
      self._ModifyVMwareLimitsConf(LIMITSFILE)

      # We killed all running vmware processes before installing,
      # so be sure to restart them.
      script = INITSCRIPTDIR/'vmware'
      if INITSCRIPTDIR and script.exists():
         self.RunCommand(script, 'stop', ignoreErrors=True)
         self.RunCommand(script, 'start')

      # serial entered by user:
      serialNumber = self.GetAnswer('serialNumber')
      if serialNumber:
          self.RunCommand(LICENSETOOL, serialNumber, PRODUCT, LICENSEVERSION)

   def PostUninstall(self, old, new, upgrade):
      # Reset hard limit for the number of open files on the system.
      self._ClearVMwareLimitsConf(LIMITSFILE, restoreEntry=True)

       # Empty out the Winger cache
      try:
         path('/var/lib/vmware/compcache').rmtree()
      except OSError:
         pass # Okay if the directory was already removed by the user

      # This seems a little counterintuitive, but we killed all running
      # vmware processes before uninstalling Workstation.  At this point
      # Player is still installed though, so we want to be
      # sure to restart the services for Player.
      script = INITSCRIPTDIR/'vmware'
      if INITSCRIPTDIR and script.exists():
         self.RunCommand(script, 'stop', ignoreErrors=True)
         self.RunCommand(script, 'start')

   def _ClearVMwareLimitsConf(self, limitsFile, restoreEntry=False):
      # Check if our section already exists at the beginning
      # of the file.  If it does clear it.
      log.Debug('nofile: Clearing limits file')
      text = limitsFile.bytes()
      newtext = re.sub(vmwareSentinel + '.*\n' + vmwareSentinel,
                       '', text, re.DOTALL)
      limitsFile.write_bytes(newtext)

      # If we're uninstalling and restoring the old file, add the
      # old limit back since we wiped it on install.
      if restoreEntry:
         oldLimit = self.GetConfig('oldNofileHardLimit')
         if oldLimit:
            log.Debug('nofile: Restoring old nofile hard limit.')
            self._WriteLimitsConfEntry(limitsFile, '*\t\thard\tnofile\t\t%s\n' % oldLimit)
            # And remove the entry from our config file.
            self.DelConfig('oldNofileHardLimit')

      self._ClearPamD(PAMLOGINFILE)

   def _RemoveMarkedLineFromFile(self, file_, entry):
      """ Remove a line wrapped in vmwareSentinel from a given file """
      text = file_.bytes()
      searchText = vmwareSentinel + entry + vmwareSentinel
      matches = re.findall(searchText, text, re.DOTALL)
      if not matches:
         return False
      newtext = re.sub(searchText, '', text, re.DOTALL)
      file_.write_bytes(newtext)
      return True

   def _WriteLimitsConfEntry(self, limitsFile, entry):
      # This function assumes that the file has already been cleared and prepped for
      # us to write an entry.
      text = limitsFile.bytes()

      # See if a limits line already exists for nofile
      # Remove comments.
      justText = re.sub('#.*\n', '', text)

      matches = re.findall('^\*.+hard.+nofile.+\d+', justText, re.MULTILINE)
      # If there is a match, we need to remove this line.
      if matches:
         # Store the old value.  We'll need to replace it later.
         self.SetConfig('oldNofileHardLimit', self.hardLimit)
         log.Debug('Removing existing hard nofile line.')
         text = re.sub('\*.+hard.+nofile.+\d+.*\n', '', text, re.MULTILINE)
      # Some systems have an '# End of file' marker.  Remove it and
      # set a flag to replace it if it's found.
      setFileEnd = False
      newText = re.sub('# End of file.*', '', text)
      if newText != text:
         setFileEnd = True
         text = newText
      # Now add in our line.
      text = text + entry
      if setFileEnd:
         text = text + '# End of file.'
      limitsFile.write_bytes(text)

   def _ClearPamD(self, pamFile):
      if pamFile.exists():
         self._RemoveMarkedLineFromFile(pamFile, pamLoginLine)

   def _WritePamD(self, pamFile):
      if pamFile.exists():
         text = pamFile.bytes()

         # Search for the entry we want:
         matches = re.findall('session\s+required\s+pam_limits.so', text)

         # If no matches were found, we need to add the entry.
         if not matches:
            newStr = text + vmwareSentinel + \
                     pamLoginLine + \
                     vmwareSentinel
            pamFile.write_bytes(newStr)

   def _ModifyVMwareLimitsConf(self, limitsFile):
      # Modify the limits.conf file to include the lines:
      # *            hard    nofile  ####
      # The validator ensures that the answer was an integer, so no need
      # to check.
      nofileHL = self.GetAnswer('nofileHardLimit')
      if nofileHL and (self.hardLimit != int(nofileHL)):
         limitsFile = Destination('/etc/security/limits.conf')
         if limitsFile.exists():
            self._ClearVMwareLimitsConf(limitsFile, restoreEntry=False)
            log.Debug('Modifying /etc/security/limits.conf hard limit from '
                      '%d to %d.', self.hardLimit, nofileHL)
            self._WriteLimitsConfEntry(limitsFile, vmwareSentinel + \
                                       '*\t\thard\tnofile\t\t%s\n' % nofileHL + \
                                       vmwareSentinel)
         self._WritePamD(PAMLOGINFILE)