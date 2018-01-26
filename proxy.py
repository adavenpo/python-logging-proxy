#!/usr/bin/env python

import sys
import logging
import threading
import BaseHTTPServer

from LoggingProxyHTTPHandler import LoggingProxyHTTPHandler

class ThreadedHTTPServer(BaseHTTPServer.HTTPServer):
    def process_request(self, request, client_address):
        thread = threading.Thread(target=self.__new_request, args=(self.RequestHandlerClass, request, client_address, self))
        thread.start()
    def __new_request(self, handlerClass, request, address, server):
        handlerClass(request, address, server)
        self.shutdown_request(request)

#server = ThreadedHTTPServer(('', 80), Handler)
#server.serve_forever()

def main(args):
    try:
        port = int(args[1])
    except IndexError:
        port = 8000
    server_address = ('', port)

    # Create logger
    logger = logging.getLogger('http proxy')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler('proxy.log')
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    #ch = logging.StreamHandler()
    #ch.setLevel(logging.ERROR)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('=' * 78 + '\n%(asctime)s - %(threadName)s - %(name)s - %(levelname)s\n' + '=' * 78 + '\n%(message)s')
    #ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    # add the handlers to logger
    #logger.addHandler(ch)
    logger.addHandler(fh)

    httpd = ThreadedHTTPServer(server_address, LoggingProxyHTTPHandler)
    httpd.serve_forever()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
