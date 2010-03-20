"""
Errors raised by L{twistedsshclient} package
"""

class SSHException (Exception):
    """
    Base Exception for all other exceptions.
    """
    pass


class BadHostKeyException (SSHException):
    """
    The host key given by the SSH server did not match what we were expecting.
    
    @param hostname: the hostname of the SSH server
    @type hostname: str
    @param key: the host key presented by the server
    @type key: L{PKey}
    @param expected_key: the host key expected
    @type expected_key: L{PKey}
    """
    def __init__(self, hostname, got_key, expected_key):
        SSHException.__init__(self, 'Host key for server %s does not match!' % hostname)
        self.hostname = hostname
        self.key = got_key
        self.expected_key = expected_key

class UnknownHostKeyException (SSHException):
    """
    The host key given by the SSH server is unknown.

    @param hostname: the hostname of the SSH server
    @type hostname: str
    @param key: the host key presented by the server
    @type key: L{PKey}
    @param expected_key: the host key expected
    @type expected_key: L{PKey}

    @since: 1.6
    """
    def __init__(self, hostname, got_key):
        SSHException.__init__(self, 'Unknown Host %s!' % hostname)
        self.hostname = hostname
        self.key = got_key

class SSHRemoteErrorException (SSHException):
    """
    Remote error received with code and description.
    
    @param code: error code
    @type code: C{int}
    @param reason: error description
    @type reason: C{str}
    """
    def __init__(self, code, reason):
        SSHException.__init__(self, 'Remote error, code: %s, reason: %s' % (code, reason))
        self.code = code
        self.reason = reason
