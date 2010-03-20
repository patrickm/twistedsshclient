"""
Example of C{GogoleChecker} protocol from L{example3_googlechecker} forwarder over L{DirectTcpIpChannelConnector}
"""

import config, sys

from twisted.internet import reactor, protocol
import sshclient, verboseprotocols
import example3_googlechecker


def connected(sshconnection):
    print "[SSHClient] Connected!"
    
    factory = example3_googlechecker.get_factory()
    connector = sshconnection.connectTCP(example3_googlechecker.HOSTNAME, example3_googlechecker.PORT, factory, 8, loseconnection_on_protocollose = True, loseconnection_on_protocolfailed = True)

client = sshclient.SSHClient(reactor)
client.load_system_host_keys()
client.set_missing_host_key_policy(sshclient.AutoAddPolicy())
client.addCallback(connected)
client.connect(config.SSH_HOSTNAME, config.SSH_PORT, username = config.SSH_USERNAME, look_for_keys = True, \
                    factory = verboseprotocols.ReconnectingClientFactory)

reactor.run()
