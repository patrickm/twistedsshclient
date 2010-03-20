"""
Example of C{GogoleChecker} protocol
"""

from twisted.web import google
from random import choice
WORDS = ['xxx', 'facebook', 'google']
HOSTNAME = 'google.com'
PORT = 80

class GoogleCheckerFactory (google.GoogleCheckerFactory):
    def __init__(self, words, *args, **kwargs):
        self.words = words
        google.GoogleCheckerFactory.__init__(self, words, *args, **kwargs)
        
    def startedConnecting(self, connector):
        print '[GoogleCheckerFactory] Started to connect.'
        print '[GoogleCheckerFactory] Word is: %s' % self.words
        google.GoogleCheckerFactory.startedConnecting(self, connector)

    def clientConnectionLost(self, connector, reason):
        print '[GoogleCheckerFactory] Lost connection.  Reason:', reason.getErrorMessage()
        google.GoogleCheckerFactory.clientConnectionLost(self, connector, reason)
    
    def clientConnectionFailed(self, connector, reason):
        print '[GoogleCheckerFactory] Connection failed. Reason:', reason.getErrorMessage()
        google.GoogleCheckerFactory.clientConnectionFailed(self, connector, reason)


def onGoogleResponse(response):
    print "[GoogleClient] Google response: %s" % response

def onGoogleError(error):
    print "[GoogleClient] Unable to query google, %s" % error

def get_factory(word = None):
    factory = GoogleCheckerFactory(word or choice(WORDS))
    factory.deferred.addCallbacks(callback=onGoogleResponse, errback=onGoogleError)
    return factory


if __name__ == '__main__':
    from twisted.internet import reactor
    factory = get_factory()
    reactor.connectTCP(HOSTNAME, PORT, factory)
    
    reactor.run()