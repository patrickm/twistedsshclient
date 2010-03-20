""" Configuration for examples, put Your own private_config to override SSH host variables """

import sys

sys.path.append('../')

try:
    from private_config import *
except Exception, e:
    SSH_HOSTNAME = 'example.com'
    SSH_PORT = 22
    SSH_USERNAME = 'example'

from twisted.python import log
# log.startLogging(sys.stdout)
