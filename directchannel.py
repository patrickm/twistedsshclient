"""
Forwards protocols through L{twisted.conch.ssh.connection.SSHConnection}

Connecting using standard methods:
    1. Calling reactor.connectTCP::

        reactor.connectTCP(host, port, factory)

    2. Behind the scenes what reactor.connectTCP does is::

        c = tcp.Connector(host, port, factory, timeout, reactor)
        c.connect()

Connecting using L{DirectTcpIpChannelConnector}:
    1. Forward protocol through ssh channel::
    
        c = DirectTcpIpChannelConnector(sshconnection, host, port, factory, timeout, reactor)
        c.connect()
"""

from twisted.conch.ssh import channel, forwarding
from twisted.internet import tcp, main, error, defer, address
from twisted.python import failure, log

__all__ = ["DirectTcpIpChannelClient", "DirectTcpIpChannelConnector"]


class DirectTcpIpChannelClient (channel.SSHChannel):
    """
    Client emulation (like L{twisted.internet.tcp.Client}) over L{twisted.conn.ssh.channel.SSHChannel}
    
    @see: L{directchannel}
    """
    name = 'direct-tcpip'

    def __init__(self, host, port, connector, reactor):
        """
        @param host: host to connect
        @type host: C{str}
        @param port: port to connect
        @type port: C{int}
        @param connector: connector
        @type connector: L{twisted.internet.tcp.Connector}
        @param reactor: reactor to use
        @type reactor: L{twisted.internet.reactor}
        """
        channel.SSHChannel.__init__(self, conn = connector.connection)
        self.host = host
        self.port = port
        self.connector = connector
        self.protocol = None
        self.connected = 0
        self.disconnected = 0
        self.disconnecting = 0
        reactor.callLater(0, self._connect)
        self.connectionLostDefer = defer.Deferred()
        self.connectionFailedDefer = defer.Deferred()
    
    def _connect(self):
        """
        Asks L{twisted.conch.sshconnection.SSHConnection} to open channel - connect
        """
        hostport = self.getHost()
        channelOpenData = forwarding.packOpen_direct_tcpip((self.host, self.port), (hostport.host, hostport.port))
        self.connector.connection.openChannel(self, channelOpenData)

    def dataReceived(self, data):
        """
        Called when we receive data.

        @type data: C{str}
        """
        if not self.disconnected:
            self.protocol.dataReceived(data)

    def channelOpen(self, specificData):
        """
        Called when the channel is opened.  specificData is any data that the
        other side sent us when opening the channel.

        @type specificData: C{str}
        """
        log.msg('opened forwarding channel %s to %s:%s' % (self.id, self.host, self.port))
        self._connectDone()

    def openFailed(self, reason):
        """
        Called when the the open failed for some reason.
        reason.desc is a string description, reason.code the the SSH error code.

        @type reason: L{error.ConchError}
        """
        log.msg('other side refused open\nreason: %s'% reason)
        self.failIfNotConnected(error.ConnectError('Connection failed'))
    
    def _connectDone(self):
        """ Called after channel is open. """
        self.protocol = self.connector.buildProtocol(self.getPeer())
        self.connected = 1
        self.disconnected = 0
        self.disconnecting = 0
        self.logstr = self.protocol.__class__.__name__ + ",client"
        self.protocol.makeConnection(self)

    def eofReceived(self):
        """ Called when the other side will send no more data. """
        channel.SSHChannel.eofReceived(self)
        # print 'DirectTcpIpChannelClient:: remote eof'
        self.loseConnection()
    
    # def closeReceived(self):
    #     """ Called when the other side has closed the channel. """
    #     channel.SSHChannel.closeReceived(self)
    #     print 'DirectTcpIpChannelClient:: closeReceived'
    # 
    # def closed(self):
    #     """
    #     Called when the channel is closed.  This means that both our side and
    #     the remote side have closed the channel.
    #     """
    #     channel.SSHChannel.closed(self)
    #     print 'DirectTcpIpChannelClient:: closed'
    
    def stopConnecting(self):
        """ Stop attempt to connect. """
        self.failIfNotConnected(error.UserError())

    def loseConnection(self, _connDone=failure.Failure(main.CONNECTION_DONE)):
        """ Close the channel if there is no buferred data.  Otherwise, note the request and return. """
        channel.SSHChannel.loseConnection(self)
        self.connectionLost(_connDone)
    
    def failIfNotConnected(self, err):
        """ Generic method called when the attemps to connect failed. """
        if (self.connected or self.disconnected or
            not hasattr(self, "connector")):
            return

        self.connector.connectionFailed(failure.Failure(err))
        del self.connector
        self.connectionFailedDefer.callback(1)

    def connectionLost(self, reason):
        """ The connection was lost. """
        if not self.connected:
            self.failIfNotConnected(error.ConnectError(string=reason))
        else:
            self.disconnected = 1
            self.connected = 0
            # self._closeSocket()
            protocol = self.protocol
            del self.protocol
            protocol.connectionLost(reason)
            self.connector.connectionLost(reason)
            self.connectionLostDefer.callback(1)

    def getPeer(self):
        """
        Return a tuple describing the other side of the connection.

        @rtype: C{IPv4Address}
        """
        return address.IPv4Address('TCP', *((self.host, self.port) + ('INET',)))
    
    def getHost(self):
        """
        Return a tuple describing our side of the connection.

        @rtype: C{IPv4Address}
        """
        return self.conn.transport.transport.getHost()
    
    def logPrefix(self):
        """ log module prefix """
        id = (self.id is not None and str(self.id)) or "unknown"
        return "SSHForwardedChannelClient (%s) on %s" % (id,
                self.conn.logPrefix())

class DirectTcpIpChannelConnector (tcp.Connector):
    """
    Connector for L{DirectTcpIpChannelClient}

    @see: L{directchannel}
    """
    
    def __init__(self, connection, host, port, factory, timeout, reactor = None, loseconnection_on_protocollose = False, loseconnection_on_protocolfailed = False):
        """
        @param connection: transport connection
        @type connection: L{twisted.conch.sshconnection.SSHConnection}
        @param host: host to connect
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
        """
        tcp.Connector.__init__(self, host, port, factory, timeout, None, reactor = reactor)
        self.connection = connection
        self.loseconnection_on_protocollose = loseconnection_on_protocollose
        self.loseconnection_on_protocolfailed = loseconnection_on_protocolfailed
    
    def _makeTransport(self):
        """ 
        Returns transport
        
        @rtype: L{DirectTcpIpChannelClient}
        """
        transport = DirectTcpIpChannelClient(self.host, self.port, self, self.reactor)
        if self.loseconnection_on_protocollose:
            transport.connectionLostDefer.addCallback(self.transportProtocolDisconnected)
        if self.loseconnection_on_protocolfailed:
            transport.connectionFailedDefer.addCallback(self.transportProtocolDisconnected)
        return transport
    
    def transportProtocolDisconnected(self, obj):
        """
        Called when L{SSHClientTransport} protocol loses or fails to connect.
        - loses connection if loseconnection_on_protocollose was set init
        - fails to connect if loseconnection_on_protocolfailed was set in init
        """
        if obj:
            log.msg("Protocol disconnected, losing connection..")
            self.connection.loseConnection()
            try:
                self.factory.stopTrying()
            except Exception, e:
                pass
