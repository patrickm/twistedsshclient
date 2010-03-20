"""
Various policies for accepting, rejecting, etc. missing server hostkeys
"""

from twisted.python import log

__all__ = ['AutoAddPolicy', 'RejectPolicy', 'WarningPolicy']


class MissingHostKeyPolicy (object):
    """
    Interface for defining the policy that L{SSHClient} should use when the
    SSH server's hostname is not in either the system host keys or the
    application's keys.  Pre-made classes implement policies for automatically
    adding the key to the application's L{HostKeys} object (L{AutoAddPolicy}),
    and for automatically rejecting the key (L{RejectPolicy}).

    This function may be used to ask the user to verify the key, for example.
    """

    def missing_host_key(self, client, hostname, key):
        """
        Called when an L{SSHClient} receives a server key for a server that
        isn't in either the system or local L{HostKeys} object.  To accept
        the key, simply return.  To reject, raised an exception (which will
        be passed to the calling application).
        """
        pass


class AutoAddPolicy (MissingHostKeyPolicy):
    """
    Policy for automatically adding the hostname and new host key to the
    local L{HostKeys} object, and saving it.  This is used by L{SSHClient}.
    """

    def missing_host_key(self, client, hostname, key):
        client.host_keys.add(hostname, key.type(), key)
        log.msg('Adding %s host key for %s: %s' % (key.type(), hostname, key.fingerprint()))


class RejectPolicy (MissingHostKeyPolicy):
    """
    Policy for automatically rejecting the unknown hostname & key.  This is
    used by L{SSHClient}.
    """

    def missing_host_key(self, client, hostname, key):
        log.msg('Rejecting %s host key for %s: %s' % (key.type(), hostname, key.fingerprint()))
        return False


class WarningPolicy (MissingHostKeyPolicy):
    """
    Policy for logging a python-style warning for an unknown host key, but
    accepting it. This is used by L{SSHClient}.
    """
    def missing_host_key(self, client, hostname, key):
        warnings.warn('Unknown %s host key for %s: %s' % (key.type(), hostname, key.fingerprint()))