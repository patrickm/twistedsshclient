"""
Basic example of L{SSHClient}
"""

import config, sys

from twisted.internet import reactor, protocol
import sshclient, verboseprotocols


client = sshclient.SSHClient(reactor)
client.load_system_host_keys()
client.set_missing_host_key_policy(sshclient.AutoAddPolicy())
client.connect(config.SSH_HOSTNAME, config.SSH_PORT, username = config.SSH_USERNAME, look_for_keys = True, factory = verboseprotocols.ClientFactory)

def onConnect(sshconnection):
    print 'connected', sshconnection
    sshconnection.loseConnection()

def onConnectFailure(result):
    print 'unable to connect', result
    reactor.stop()

client.addCallback(onConnect)
client.addErrback(onConnectFailure)

reactor.run()
