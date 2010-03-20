"""
Basic example of L{SSHClient} with forwarded protocol using L{DirectTcpIpChannelConnector}
"""

import config, sys

from twisted.internet import reactor, protocol
import sshclient, verboseprotocols
from directchannel import DirectTcpIpChannelConnector


class SimpleSMTPProtocol (protocol.Protocol):
    helo_sent = False
    
    def connectionMade(self):
        print '[SimpleSMTPProtocol] connection made', self.transport
        self.factory.connected()

    def dataReceived(self, data):
        print "[SimpleSMTPProtocol] Received: %s" % data.strip()
        if not self.helo_sent:
            self.helo_sent = True
            self.transport.write("helo localhost\n")
            self.transport.write("quit\n")
        # self.transport.loseConnection()

    # def connectionLost(self, reason):
    #     print '[Echo] Lost connection.  Reason:', reason

class SimpleSMTPFactory (protocol.ReconnectingClientFactory):
    protocol = SimpleSMTPProtocol

    def connected(self):
        self.resetDelay()

    def startedConnecting(self, connector):
        print
        print '[SimpleSMTPFactory] Started to connect.'
    
    def clientConnectionLost(self, connector, reason):
        print '[SimpleSMTPFactory] Lost connection.  Reason:', reason.getErrorMessage()
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
    
    def clientConnectionFailed(self, connector, reason):
        print '[SimpleSMTPFactory] Connection failed. Reason:', reason.getErrorMessage()
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
    


def connected(sshconnection):
    print "[SSHClient] Connected!"
    connector = DirectTcpIpChannelConnector(sshconnection, 'smtp.google.com', 25, SimpleSMTPFactory(), 10, reactor)
    connector.connect()
    ## or:
    ## connector = sshconnection.connectTCP('smtp.google.com', 25, SimpleSMTPFactory(), 10)
    ##

client = sshclient.SSHClient(reactor)
client.load_system_host_keys()
client.set_missing_host_key_policy(sshclient.AutoAddPolicy())
client.addCallback(connected)
client.connect(config.SSH_HOSTNAME, config.SSH_PORT, username = config.SSH_USERNAME, look_for_keys = True, factory = verboseprotocols.ClientFactory)

reactor.run()
