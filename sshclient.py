"""
L{SSHClient} is a high-level representation of a session with an SSH server
based on usage and interface of C{paramiko.client.SSHClient}.
"""

import os, sys, warnings, getpass
from twisted.conch.ssh import transport, userauth, connection, keys
from twisted.internet import defer, protocol, reactor
from twisted.python import log, failure

from directchannel import DirectTcpIpChannelConnector
from hostkeys import HostKeys
from errors import *
from policies import *

SSH_PORT = 22

__all__ = ['SSHClient']


class SSHClient (object):
    """
    A high-level representation of a session with an SSH server based on usage and interface of C{paramiko.client.SSHClient}.
    This class wraps L{SSHClientTransport} L{SSHUserAuthClient} L{SSHConnection} to take care of most
    aspects of authenticating and opening channels.  A typical use case is::

        client = SSHClient()
        client.load_system_host_keys()
        client.connect('ssh.example.com')

        def onConnect(sshconnection):
            print 'connected', sshconnection
            sshconnection.loseConnection()

        def onConnectFailure(result):
            print 'unable to connect', result

        client.addCallback(onConnect)
        client.addErrback(onConnectFailure)
    """
    def __init__(self, reactor):
        """
        @param reactor: reactor to use
        @type reactor: L{twisted.internet.reactor}
        """
        
        super(SSHClient, self).__init__()
        self.reactor = reactor
        self.system_host_keys = HostKeys()
        self.host_keys = HostKeys()
        self.missing_host_key_policy = RejectPolicy()
        self.closeRequest = defer.Deferred()
        self.callback = None
        self.errback = None

        self.hostname = None
        self.port = None
        self.username = None
        self.password = None
        self.pkey = None
        self.key_filenames = []
        self.look_for_keys = False
    
    def load_system_host_keys(self, filename=None):
        """
        Load host keys from a system (read-only) file.
        
        This method can be called multiple times.  Each new set of host keys
        will be merged with the existing set (new replacing old if there are
        conflicts).

        If C{filename} is left as C{None}, an attempt will be made to read
        keys from the user's local "known hosts" file, as used by OpenSSH,
        and no exception will be raised if the file can't be read.  This is
        probably only useful on posix.

        @param filename: the filename to read, or C{None}
        @type filename: str

        @raise IOError: if a filename was provided and the file could not be
            read
        """

        if filename is None:
            filename = os.path.expanduser('~/.ssh/known_hosts')
            try:
                self.system_host_keys.load(filename)
            except IOError:
                pass
            return
        self.system_host_keys.load(filename)

    def load_host_keys(self, filename):
        """
        Load host keys from a local host-key file.  Host keys read with this
        method will be checked I{after} keys loaded via L{load_system_host_keys}.
        The missing host key policy L{AutoAddPolicy} adds keys to this set and
        saves them, when connecting to a previously-unknown server.

        This method can be called multiple times.  Each new set of host keys
        will be merged with the existing set (new replacing old if there are
        conflicts).  When automatically saving, the last hostname is used.

        @param filename: the filename to read
        @type filename: str

        @raise IOError: if the filename could not be read
        """
        self.host_keys.load(filename)

    def get_host_keys(self):
        """
        Get the local L{HostKeys} object.  This can be used to examine the
        local host keys or change them.

        @return: the local host keys
        @rtype: L{HostKeys}
        """
        return self.host_keys
    
    def set_missing_host_key_policy(self, policy):
        """
        Set the policy to use when connecting to a server that doesn't have a
        host key in either the system or local L{HostKeys} objects.  The
        default policy is to reject all unknown servers (using L{RejectPolicy}).
        You may substitute L{AutoAddPolicy} or write your own policy class.

        @param policy: the policy to use when receiving a host key from a
            previously-unknown server
        @type policy: L{MissingHostKeyPolicy}
        """
        self.missing_host_key_policy = policy

    def close(self):
        """
        Close this SSHClient and its underlying L{SSHClientTransport}.
        """
        self.closeRequest.callback(1)
        self.closeRequest = defer.Deferred()
    disconnect = close

    def connect(self, hostname, port = SSH_PORT, username = None, password = None, pkey = None, key_filename = None, timeout = None, look_for_keys = True, factory = protocol.ClientFactory):
        """
        Connect to an SSH server and authenticate to it.  The server's host key
        is checked against the system host keys (see L{load_system_host_keys})
        and any local host keys (L{load_host_keys}).  If the server's hostname
        is not found in either set of host keys, the missing host key policy
        is used (see L{set_missing_host_key_policy}).  The default policy is
        to reject the key and raise an L{SSHException}.

        Authentication is attempted in the following order of priority:

            - The C{pkey} or C{key_filename} passed in (if any)
            - Any key we can find through an SSH agent
            - Any "id_rsa" or "id_dsa" key discoverable in C{~/.ssh/}
            - Plain username/password auth, if a password was given

        TODO: If a private key requires a password to unlock it, and a password is
        passed in, that password will be used to attempt to unlock the key.

        @param hostname: the server to connect to
        @type hostname: str
        @param port: the server port to connect to
        @type port: int
        @param username: the username to authenticate as (defaults to the
            current local username)
        @type username: str
        @param password: a password to use for authentication or for unlocking
            a private key
        @type password: str
        @param pkey: an optional private key to use for authentication
        @type pkey: L{twisted.conch.ssh.keys.Key}
        @param key_filename: the filename, or list of filenames, of optional
            private key(s) to try for authentication
        @type key_filename: str or list(str)
        @param timeout: an optional timeout (in seconds) for the TCP connect
        @type timeout: float
        @param look_for_keys: set to False to disable searching for discoverable
            private key files in C{~/.ssh/}
        @type look_for_keys: bool
        @param factory: factory to use, default is: L{twisted.internet.protocol.ClientFactory}
        @type factory: L{twisted.internet.protocol.ClientFactory}
        """
        
        new_factory = type('SSHClientSpecializedFactoryOf%s' % factory.__name__, (SSHClientSpecializedFactory, factory), {})()
        new_factory.protocol = SSHClientTransport
        
        if username is None:
            username = getpass.getuser()
        
        if key_filename is None:
            key_filenames = []
        elif isinstance(key_filename, (str, unicode)):
            key_filenames = [ key_filename ]
        else:
            key_filenames = key_filename
        
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.pkey = pkey
        self.key_filenames = key_filenames
        self.look_for_keys = look_for_keys
        
        new_factory.sshclient = self
        self.reactor.connectTCP(hostname, port, new_factory)
        return self
    
    def addCallback(self, callback):
        """ Adds callback called after successful connection. Callback is called by L{SSHConnection.serviceStarted}"""
        self.callback = callback
    
    def addErrback(self, errback):
        """ Adds errorback called after failed connection. Errorback is called before factory methods: C{clientConnectionLost} and C{clientConnectionFailed}"""
        self.errback = errback
    
    def removeCallback(self):
        """ Removes current callback """
        self.callback = None
    
    def removeErrback(self):
        """ Removes current errorback """
        self.errback = None

    def processCallback(self, sshconnection):
        """ Helper method for processing callback """
        if self.callback:
            self.callback(sshconnection)
    
    def processErrback(self, reason):
        """ Helper method for processing errorback """
        if self.errback:
            self.errback(reason)

class SSHClientSpecializedFactory (object):
    """ Specialized factory with support for calling errbacks by L{SSHClient}"""
    
    def buildProtocol(self, addr):
        """ Builds protocol """
        proto = super(SSHClientSpecializedFactory, self).buildProtocol(addr)
        proto.sshclient = self.sshclient
        return proto

    def clientConnectionLost(self, connector, reason):
        """ Calls L{SSHClient} errorback before invoking orginal factory clientConnectionLost method """
        if isinstance(reason, SSHException) or (isinstance(reason, failure.Failure) and reason.check(SSHException)):
            self.sshclient.processErrback(reason)
        return super(SSHClientSpecializedFactory, self).clientConnectionLost(connector, reason)

    def clientConnectionFailed(self, connector, reason):
        """ Calls L{SSHClient} errorback before invoking orginal factory clientConnectionLost method """
        if isinstance(reason, SSHException) or (isinstance(reason, failure.Failure) and reason.check(SSHException)):
            self.sshclient.processErrback(reason)
        return super(SSHClientSpecializedFactory, self).clientConnectionFailed(connector, reason)

class SSHClientTransport (transport.SSHClientTransport):
    """ SSH Transport with hostkeys verification. """
    
    def connectionSecure(self):
        """
        Called when the encryption has been set up.  Generally,
        requestService() is called to run another service over the transport.
        """
        self.sshclient.closeRequest.addCallback(self.closeRequested)
        self.requestService(SSHUserAuthClient(self.sshclient, SSHConnection()))
    
    def closeRequested(self, result):
        """ Callback for L{SSHClient.closeRequest}, loses current connection. """
        if result:
            self.transport.loseConnection()
            self.loseConnection()

    def verifyHostKey(self, hostKey, fingerprint):
        """ Host Keys verification """
        server_key = keys.Key.fromString(hostKey)
        keytype = server_key.type()

        if self.sshclient.port == SSH_PORT:
            server_hostkey_name = self.sshclient.hostname
        else:
            server_hostkey_name = "[%s]:%d" % (self.sshclient.hostname, self.sshclient.port)
        
        our_server_key = self.sshclient.system_host_keys.get(server_hostkey_name, {}).get(keytype, None)
        if our_server_key is None:
            our_server_key = self.sshclient.host_keys.get(server_hostkey_name, {}).get(keytype, None)
        if our_server_key is None:
            status = self.sshclient.missing_host_key_policy.missing_host_key(self.sshclient, server_hostkey_name, server_key)
            if status is False:
                self.transport.connectionLost(failure.Failure(UnknownHostKeyException(self.sshclient.hostname, server_key)))
                return defer.fail(0)
            our_server_key = server_key
        
        if server_key != our_server_key:
            self.transport.connectionLost(failure.Failure(BadHostKeyException(self.sshclient.hostname, server_key, our_server_key)))
            return defer.fail(0)

        
        return defer.succeed(1)

    # def connectionLost(self, reason):
    #     print '[SSHClientTransport] Lost connection.  Reason:', reason

    def receiveError(self, reasonCode, description):
        """
        Called when we receive a disconnect error message from the other
        side. Calls connectionLost on transport with L{SSHRemoteErrorException}.

        @param reasonCode: the reason for the disconnect, one of the
                           DISCONNECT_ values.
        @type reasonCode: C{int}
        @param description: a human-readable description of the
                            disconnection.
        @type description: C{str}
        
        """
        return self.transport.connectionLost(failure.Failure(SSHRemoteErrorException(reasonCode, description)))

class SSHConnection (connection.SSHConnection):
    """
    An implementation of the 'ssh-connection' service.  It is used to
    multiplex multiple channels over the single SSH connection.
    
    Notifies L{SSHClient} when service is started.
    """

    def serviceStarted(self):
        """ Calls L{SSHClient} callback when service is started. """
        self.transport.sshclient.processCallback(self)

    def loseConnection(self):
        """ Loses transport connection. """
        self.transport.loseConnection()
    
    def connectTCP(self, host, port, factory, timeout, reactor = None, loseconnection_on_protocollose = False, loseconnection_on_protocolfailed = False):
        """
        Helper method for L{DirectTcpIpChannelConnector}

        @see: L{directchannel}
        
        @param host: hostname to connect
        @type host: C{str}
        @param port: port to connect
        @type port: C{int}
        @param factory: client factory to use
        @type factory: L{twisted.internet.protocol.ClientFactory}
        @param timeout: timeout
        @type timeout: C{int}
        @param reactor: reactor to use
        @type reactor: L{twisted.internet.reactor}
        @param loseconnection_on_protocollose: when set loses L{twisted.conch.sshconnection.SSHConnection} when channel is loses it's own connection
        @param loseconnection_on_protocolfailed: when set loses L{twisted.conch.sshconnection.SSHConnection} when channel fails to connect
        @return: instance of C{DirectTcpIpChannelConnector}
        @rtype: L{DirectTcpIpChannelConnector}
        """
        reactor = reactor or self.transport.sshclient.reactor
        connector = DirectTcpIpChannelConnector(self, host, port, factory, timeout, reactor, loseconnection_on_protocollose, loseconnection_on_protocolfailed)
        connector.connect()
        return connector

class SSHUserAuthClient (userauth.SSHUserAuthClient):
    """
    A service implementing the client side of 'ssh-userauth'.
    Supports password and multiple private keys verification (with password)
    """

    keys_to_try = ['id_dsa', 'id_rsa']
    keys_iter = None
    current_key = None

    def __init__(self, sshclient, instance):
        """
        @param sshclient: Instance of L{SSHClient}
        @param instance: Instance of L{twisted.conch.ssh.service.SSHService} here: L{SSHConnection}
        """
        userauth.SSHUserAuthClient.__init__(self, sshclient.username, instance)
        self.sshclient = sshclient
        self.found_keys = []
        self.found_keys_iter = None
        self.current_pkey = None
        self.collect_keys()
    
    def collect_keys(self):
        """ Loads private keys from ~/.ssh/ or ~/ssh/ directory """

        def load_key_from_file(key_filename):
            """ Helper function for loading keys with password """
            try:
                key = keys.Key.fromFile(key_filename)
            except keys.EncryptedKeyError, e:
                if self.sshclient.password:
                    try:
                        key = keys.Key.fromFile(key_filename, passphrase = self.sshclient.password)
                    except keys.EncryptedKeyError, e:
                        raise e
                else:
                    raise e
            return key
        
        from itertools import cycle
        found_keys = []
        
        if self.sshclient.pkey is not None:
            log.msg('Adding SSH key %s' % self.sshclient.pkey.fingerprint())
            found_keys.append(self.sshclient.pkey)
        
        for key_filename in self.sshclient.key_filenames:
            pkey = load_key_from_file(key_filename)
            log.msg('Adding SSH key %s from %s' % (pkey.fingerprint(), key_filename))
            found_keys.append(pkey)
            
        if self.sshclient.look_for_keys:
            for pkey_name in self.keys_to_try:
                pkey_file = os.path.expanduser('~/.ssh/%s' % pkey_name)
                if os.path.isfile(pkey_file):
                    pkey = load_key_from_file(pkey_file)
                    log.msg('Adding SSH key %s from %s' % (pkey.fingerprint(), pkey_file))
                    found_keys.append(pkey)

                pkey_file = os.path.expanduser('~/ssh/%s' % pkey_name)
                if os.path.isfile(pkey_file):
                    pkey = load_key_from_file(pkey_file)
                    log.msg('Adding SSH key %s from %s' % (pkey.fingerprint(), pkey_file))
                    found_keys.append(pkey)
            
        self.found_keys = found_keys
        self.found_keys_iter = cycle(self.found_keys)


    def getPassword(self):
        """ Returns password if set """
        if self.sshclient.password:
            return defer.succeed(self.sshclient.password)
        return None
    
    def getPublicKey(self):
        """ Return a public key, allows key rotation - methods gets called multiple times if key is not valid """
        if not self.found_keys:
            return

        self.current_pkey = self.found_keys_iter.next()
        return self.current_pkey.public()

    def getPrivateKey(self):
        """ Return a private key, allows key rotation - methods gets called multiple times if key is not valid """
        if not self.current_pkey:
            return
        
        return defer.succeed(self.current_pkey)
