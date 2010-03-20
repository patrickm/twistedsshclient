Twisted SSHClient
=================

**SSHClient** is a high-level representation of a session with an SSH server based on usage and interface of paramiko.client.SSHClient.

Package includes **DirectTcpIpChannelConnector** - a Connector allowing protocol forwarding through twisted.conch.ssh.connection.SSHConnection.

Usage:
------

*Very basic usage*


	def onConnect(sshconnection):
	    mySuperFactory = ...
	    connector = sshconnection.connectTCP('smtp.google.com', 25, mySuperFactory, timeout = 8)

	client = sshclient.SSHClient(reactor)
	client.load_system_host_keys()
	client.set_missing_host_key_policy(sshclient.AutoAddPolicy())
	client.addCallback(onConnect)
	client.connect('example.com', username = 'test', look_for_keys = True)


*For more see examples/example[1..].py*


Author
------

* Patrick Majewski <patrykm@me.com>

