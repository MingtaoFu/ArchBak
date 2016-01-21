#
# Copyright 2010 VMware, Inc.  All rights reserved. -- VMware Confidential
#
# Workstation Server component
#
DEST = LIBDIR/'vmware'
conf = DEST/'setup/vmware-config'

class VmwareWorkstationServer(Installer):
   def PreTransactionInstall(self, old, new, upgrade):
      gui.SetBannerImage('extras/artwork/welcome-vmis.bmp')
      gui.SetHeaderImage('extras/artwork/setup-vmis.ico')

   def InitializeQuestions(self, old, new, upgrade):
      defaultUser = self.GetAnswer('hostdUser')
      if defaultUser:
         qlevel = 'CUSTOM'
      else:
         qlevel = 'REGULAR'
         # Find a good default from the sudo environment variable.
         # If it can't be found, use root.
         try:
            defaultUser = ENV.get('SUDO_USER')
         except:
            pass
         if not defaultUser:
            defaultUser = 'root'
      self.AddQuestion('TextEntry',
                       key='hostdUser',
                       text='',
                       default=defaultUser,
                       required=True,
                       header='Please enter the user that will initially connect to Workstation Server.'
                              ' Without setting this correctly, you will not be able to share VMs with other users.',
                       footer='Additional users and administrators can be configured later in Workstation by selecting'
                              ' "Shared VMs" and clicking "Permissions".',
                       level=qlevel)

      datastore = self.GetAnswer('datastore')
      if datastore:
         qlevel = 'CUSTOM'
      else:
         qlevel = 'REGULAR'
         datastore='/var/lib/vmware/Shared VMs'
      self.AddQuestion('Directory',
                       key='datastore',
                       text='Please choose a directory for your shared virtual machines.',
                       default=datastore,
                       required=True,
                       mustExist=False,
                       level=qlevel)

      httpsPort = self.GetAnswer('httpsPort')
      if httpsPort:
         qlevel = 'CUSTOM'
      else:
         qlevel = 'REGULAR'
      self.AddQuestion('PortEntry',
                       key='httpsPort',
                       text='Please enter the port to use for https access to Workstation Server.',
                       process='hostd',
                       default='443',
                       label='HTTPS port:',
                       required=True,
                       level=qlevel)


   def InitializeInstall(self, old, new, upgrade):
      self.AddTarget('File', 'bin/*', DEST/'bin')
      self.AddTarget('File', 'sbin/*', SBINDIR)
      self.AddTarget('File', 'lib/*', DEST/'lib')
      self.AddTarget('File', 'hostd/*', DEST/'hostd')
      self.AddTarget('File', 'env/*', DEST/'env')
      self.AddTarget('File', 'vmware-hostd', BINDIR/'vmware-hostd')
      self.AddTarget('File', 'vmware-vim-cmd', BINDIR/'vmware-vim-cmd')
      self.AddTarget('File', 'vmware-wssc-adminTool', BINDIR/'vmware-wssc-adminTool')
      self.AddTarget('File', 'etc/*', SYSCONFDIR)

      # Binary links
      self.AddTarget('Link', DEST/'bin/vmware-hostd', DEST/'bin/vmware-vim-cmd')

      # Library links
      self.AddTarget('Link', DEST/'lib/diskLibWrapper.so/diskLibWrapper.so',
                     LIBDIR/'diskLibWrapper.so')

      # pam.d links
      systypeMod = self.LoadInclude('systemType')
      (sysName, sysVersion, sysExtra) = systypeMod.SystemType()
      if sysName in ['CentOS', 'Fedora', 'RHEL']:
         self.AddTarget('File', 'extras/pam.d.authd.rhel', SYSCONFDIR/'pam.d/vmware-authd')
      else:
         self.AddTarget('File', 'extras/pam.d.authd', SYSCONFDIR/'pam.d/vmware-authd')

      # Set permissions
      self.SetPermission(BINDIR/'vmware-hostd', BINARY)
      self.SetPermission(BINDIR/'vmware-vim-cmd', BINARY)
      self.SetPermission(BINDIR/'vmware-wssc-adminTool', BINARY)
      self.SetPermission(DEST/'bin/openssl', BINARY)
      self.SetPermission(DEST/'bin/vmware-hostd', BINARY)
      self.SetPermission(DEST/'bin/vmware-wssc-adminTool', BINARY)
      self.SetPermission(DEST/'bin/configure-hostd.sh', BINARY)
      self.SetPermission(SYSCONFDIR/'init.d/vmware-workstation-server', BINARY)
      self.SetPermission(SYSCONFDIR/'vmware/ssl', 0600)

   def PostInstall(self, old, new, upgrade):
      # If necessary, create the Shared VMs directory and make sure
      # the access bits are set correctly.
      datastore = path(self.GetAnswer('datastore'))
      if datastore and datastore != '':
         try:
            datastore.makedirs()
         except OSError, e:
            # If the directory already exists, it will throw an OSError.
            pass
         datastore.chmod(01777)

      # If we're not upgrading, set up the following four files.  Pull them from the component's
      # config/ directory and write them to their proper location with values subbed in.
      # Their existence is managed by this control file, not by the installer.
      # Look for: "if not foo.exists():"
      # Fill in the default user in authorization.xml
      defaultUser = self.GetAnswer('hostdUser')
      authfile = path(SYSCONFDIR/'vmware/hostd/authorization.xml')
      txt = self.GetFileText('config/etc/vmware/hostd/authorization.xml')
      newtxt = re.sub('<ACEDataUser>root</ACEDataUser>',
                      '<ACEDataUser>%s</ACEDataUser>' % defaultUser,
                      txt, re.DOTALL)
      if not authfile.exists():
         authfile.write_bytes(newtxt)

      # Fill in the datastore in datastores.xml
      datastore = self.GetAnswer('datastore')
      if not datastore:
         datastore = ''
      # We need to escape backslashes, the re module has issues with them.
      datastore = re.sub('\\\\', '\\\\\\\\', datastore)
      dstorefile = path(SYSCONFDIR/'vmware/hostd/datastores.xml')
      txt = self.GetFileText('config/etc/vmware/hostd/datastores.xml')
      newtxt1 = re.sub('##{DS_NAME}##', 'standard', txt)
      newtxt2 = re.sub('##{DS_PATH}##', datastore, newtxt1)
      if not dstorefile.exists():
         dstorefile.write_bytes(newtxt2)

      # Fill in entries in proxy.xml
      proxyfile = path(SYSCONFDIR/'vmware/hostd/proxy.xml')
      txt = self.GetFileText('config/etc/vmware/hostd/proxy.xml')
      newtxt = re.sub('##{PIPE_PREFIX}##', '/var/run/vmware/', txt)
      # Add two new entries to proxy.xml for the httpPort and httpsPort.
      # HTTP will always be -1 (disabled). The user may have chosen a
      # non-default entry for https.
      httpsPort = self.GetAnswer('httpsPort')
      if not httpsPort:
         # Provide a sane default
         httpsPort = '443'
      newtxt = re.sub('##{HTTP_PORT}##', '-1', newtxt)
      newtxt = re.sub('##{HTTPS_PORT}##', httpsPort, newtxt)
      if not proxyfile.exists():
         proxyfile.write_bytes(newtxt)

      # Fill in entries in config.xml
      configfile = path(SYSCONFDIR/'vmware/hostd/config.xml')
      txt = self.GetFileText('config/etc/vmware/hostd/config.xml')
      hostdReplacement = { 'BUILD_CFGDIR': SYSCONFDIR/'vmware/hostd/',
                           'CFGALTDIR': SYSCONFDIR/'vmware/hostd/',
                           'CFGDIR': SYSCONFDIR/'vmware/',
                           'ENABLE_AUTH': 'true',
                           'HOSTDMODE': 'ws',
                           'HOSTD_CFGDIR': SYSCONFDIR/'vmware/hostd/',
                           'HOSTD_MOCKUP': 'false',
                           'LIBDIR': DEST,
                           'LIBDIR_INSTALLED': str(DEST) + '/',
                           'LOGDIR': '/var/log/vmware/',
                           'LOGLEVEL': 'verbose',
                           'MOCKUP': 'mockup-host-config.xml',
                           'PLUGINDIR': './',
                           'SHLIB_PREFIX': 'lib',
                           'SHLIB_SUFFIX': '.so',
                           'USE_BLKLISTSVC': 'false',
                           'USE_CBRCSVC': 'false',
                           'USE_CIMSVC': 'false',
                           'USE_DIRECTORYSVC': 'false',
                           'USE_DIRECTORYSVC_MOCKUP': 'false',
                           'USE_DYNAMIC_PLUGIN_LOADING': 'false',
                           'USE_DYNAMO': 'false',
                           'USE_DYNSVC': 'false',
                           'USE_GUESTSVC': 'false',
                           'USE_HBRSVC': 'false',
                           'USE_HBRSVC_MOCKUP': 'false',
                           'USE_HOSTSVC_MOCKUP': 'false',
                           'USE_HTTPNFCSVC': 'false',
                           'USE_HTTPNFCSVC_MOCKUP': 'false',
                           'USE_LICENSESVC_MOCKUP': 'false',
                           'USE_NFCSVC': 'true',
                           'USE_NFCSVC_MOCKUP': 'false',
                           'USE_OVFMGRSVC': 'true',
                           'USE_PARTITIONSVC': 'false',
                           'USE_SECURESOAP': 'false',
                           'USE_SNMPSVC': 'false',
                           'USE_SOLO_MOCKUP': 'false',
                           'USE_STATSSVC': 'false',
                           'USE_STATSSVC_MOCKUP': 'false',
                           'USE_VCSVC_MOCKUP': 'false',
                           'USE_VDISKSVC': 'false',
                           'USE_VDISKSVC_MOCKUP': 'false',
                           'USE_VSLMSVC': 'false',
                           'USE_VSLMSVC_MOCKUP': 'false',
                           'USE_VMSVC_MOCKUP': 'false',
                           'VM_INVENTORY': 'vmInventory.xml',
                           'VM_RESOURCES': 'vmResources.xml',
                           'WEBSERVER_PORT_ENTRY': '', # no webserver for hosted
                           'WORKINGDIR': './', }
      newtxt = txt
      for key,value in hostdReplacement.iteritems():
         newtxt = re.sub('##{%s}##' % key, value, newtxt)
      # Always replace config.xml
      configfile.write_bytes(newtxt)

      # Fill in entries in environments.xml
      envfile = path(SYSCONFDIR/'vmware/hostd/environments.xml')
      txt = envfile.bytes()
      newtxt = re.sub('##{ENV_LOCATION}##', SYSCONFDIR/'vmware/hostd/env/', txt)
      envfile.write_bytes(newtxt)

      # Find an open port for authd
      authdPort = 902

      lsof = self.RunCommand('/usr/bin/lsof', '-ni4', '-P', ignoreErrors=True, noLogging=True)
      if lsof.retCode == 0:
         allPorts = re.findall('^(\S+)\s+\d+\s+\S+\s+\S+\s+IP..\s+\d+\s+\S+\s+\S+\s+\*\:(\S+)',
                               lsof.stdout, re.MULTILINE)
         scanRange = range(1,1024)
         scanRange.reverse() # Scan down from 1023, we'd rather not grab a low port #.
         scanRange.insert(0, authdPort) # Add 902 to the beginning of the list.  We prefer this port.
         for port in scanRange:
            # Find an open port.
            inUseBy = None
            for checkPort in allPorts:
               (name, portNum) = checkPort
               if str(port) == portNum and name != 'vmware-au':
                  inUseBy = name
                  break
            if inUseBy is None:
               authdPort = port
               break

      # Fill in entries in clients.xml
      # These are all known values at the moment, but sub in here for consistency rather than in the Makefile
      clientfile = path(DEST/'hostd/docroot/client/clients.xml')
      txt = clientfile.bytes()
      newtxt = re.sub('@@AUTHD_PORT@@', '%s' % authdPort, txt)
      newtxt = re.sub('@@VICLIENT_URL@@', 'http://vsphereclient.vmware.com/vsphereclient/released/3/2/4/3/2/6/VMware-viclient-all-5.0.0-324326.exe', newtxt)
      clientfile.write_bytes(newtxt)

      # Now add config entries to VMware config
      self.RunCommand(conf, '-s', 'authd.client.port', '%s' % authdPort)
      self.RunCommand(conf, '-s', 'authd.proxy.nfc', 'vmware-hostd:ha-nfc')

      inits = self.LoadInclude('initscript')
      services = '$network vmware vmware-USBArbitrator'
      if self._hasHalDaemon():
         services += ' haldaemon'
      inits.ConfigureService('vmware-workstation-server',
                             'This services starts and stops the Workstation as a Server daemon.',
                             services, # Start
                             services, # Stop
                             '',
                             '',
                             55,
                             6)

   def PostTransactionInstall(self, old, new, upgrade):
      # Start up the HostD service.  This *must* happen in PostTransaction.
      # HostD uses modconfig to make sure the kernel modules are built before
      # it's run.  This can't happen during the other install phases because
      # VMIS has locked the database and modconfig invokes another version of
      # VMIS to register the compiled modules.
      script = INITSCRIPTDIR/'vmware-workstation-server'
      if INITSCRIPTDIR and script.exists():
         self.RunCommand(script, 'restart', ignoreErrors=True)

   def PreUninstall(self, old, new, upgrade):
      # Stop the HostD service
      script = INITSCRIPTDIR/'vmware-workstation-server'
      if INITSCRIPTDIR and script.exists():
         self.RunCommand(script, 'stop', ignoreErrors=True)

      inits = self.LoadInclude('initscript')
      inits.DeconfigureService('vmware-workstation-server')

   def PostUninstall(self, old, new, upgrade):
      # Try to remove the Shared VMs directory
      datastore = path(self.GetAnswer('datastore'))
      try:
         datastore.removedirs()
      except OSError, e:
         # If the directory cannot be removed, it will throw an OSError
         pass

      # Remove config files if we are not upgrading.  These files are managed by this
      # control file and not by the installer.
      keepConfig = self.GetConfig('keepConfigOnUninstall', component='vmware-installer')
      if not upgrade and keepConfig != 'yes':
         # Config files
         authfile = path(SYSCONFDIR/'vmware/hostd/authorization.xml')
         dstorefile = path(SYSCONFDIR/'vmware/hostd/datastores.xml')
         proxyfile = path(SYSCONFDIR/'vmware/hostd/proxy.xml')
         configfile = path(SYSCONFDIR/'vmware/hostd/config.xml')
         inventoryfile = path(SYSCONFDIR/'vmware/hostd/vmInventory.xml')
         autostartfile = path(SYSCONFDIR/'vmware/hostd/vmAutoStart.xml')
         # Certificate Files
         certfile = path(SYSCONFDIR/'vmware/ssl/rui.crt')
         keyfile = path(SYSCONFDIR/'vmware/ssl/rui.key')
         for fil in [authfile, dstorefile, proxyfile, configfile, inventoryfile,
                     autostartfile, certfile, keyfile]:
            fil.remove(ignore_errors=True)

      # Remove config entries
      self.RunCommand(conf, '-d', 'authd.client.port')
      self.RunCommand(conf, '-d', 'authd.proxy.nfc')
      self.RunCommand(conf, '-d', 'authd.soapserver')

      # Remove hostd stats files created in run time
      statsdir = "/var/lib/vmware/hostd/stats"
      statsfiles = ["hostAgentStats-20.stats", "hostAgentStats.idMap", "hostAgentStats.xml"]
      for statsfile in statsfiles:
         path('%s/%s' % (statsdir, statsfile)).remove(ignore_errors=True)
      # Also try to remove the directory if not empty
      try:
         path(statsdir).rmdir()
      except OSError:
         # Either doesn't exist or the directory isn't empty.
         log.Debug(u'Unable to remove %s', statsdir)
         pass


   def _hasHalDaemon(self):
      halDaemon = INITSCRIPTDIR/'haldaemon'
      if halDaemon.exists():
         return True
      return False
