"""
Extended, more verbose ClientFactory and ReconnectingClientFactory

Extended versions print info on startedConnecting, clientConnectionLost, clientConnectionFailed
"""

from twisted.internet import reactor, protocol

def format_reason(reason):
    """ formats reason helper function """
    return reason.getErrorMessage()

class ClientFactory (protocol.ClientFactory):
    """ Verbose version of ClientFactory """
    def startedConnecting(self, connector):
        print
        print '[SSHClient-ClientFactory] Connecting..'
        return protocol.ClientFactory.startedConnecting(self, connector)
    
    def clientConnectionLost(self, connector, reason):
        print '[SSHClient-ClientFactory] Lost connection.  Reason:', format_reason(reason)
        return protocol.ClientFactory.clientConnectionLost(self, connector, reason)
    
    def clientConnectionFailed(self, connector, reason):
        print '[SSHClient-ClientFactory] Connection failed. Reason:', format_reason(reason)
        return protocol.ClientFactory.clientConnectionFailed(self, connector, reason)


class ReconnectingClientFactory (protocol.ReconnectingClientFactory):
    """ Verbose version of ReconnectingClientFactory """
    def startedConnecting(self, connector):
        print
        print '[SSHClient-ClientFactory] Connecting..'
        return protocol.ReconnectingClientFactory.startedConnecting(self, connector)
    
    def clientConnectionLost(self, connector, reason):
        print '[SSHClient-ClientFactory] Lost connection.  Reason:', format_reason(reason)
        return protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
    
    def clientConnectionFailed(self, connector, reason):
        print '[SSHClient-ClientFactory] Connection failed. Reason:', format_reason(reason)
        return protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
    