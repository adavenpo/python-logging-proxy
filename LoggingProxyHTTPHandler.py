import sys
import gzip
import logging
import requests
import StringIO
import traceback
import BaseHTTPServer

LOG = None

def rewrite_headers(headers):
    # Don't accept stuff that original request didn't accept
    if not 'accept-encoding' in headers:
        headers['accept-encoding'] = 'identity'
    result = dict()
    for k, v in headers.items():
        newk = '-'.join(map(lambda x: x.capitalize(), k.split('-')))
        result[newk] = v
    if 'Content-Encoding' in result and result['Content-Encoding'].lower() == 'gzip':
        del result['Content-Encoding']
    return result

class LoggingProxyHTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    # send_response pretty similar to BaseHTTPServer send_response
    # but without Server or Date headers
    def send_response(self, code, message=None):
        if message is None:
            if code in self.responses:
                message = self.responses[code][0]
            else:
                message = ''
        if self.request_version != 'HTTP/0.9':
            response = "{0} {1} {2}\r\n".format(self.protocol_version,
                                                code, message)
            self.wfile.write(response)

    def respond(self, response):
        if response.status_code < 400:
            self.send_response(response.status_code)
        else:
            self.send_error(response.status_code)
        for k, v in rewrite_headers(response.headers).items():
            self.send_header(k, v)
        self.end_headers()

        output = response.content
        # handle gzip
        # http://stackoverflow.com/questions/8506897/how-do-i-gzip-compress-a-string-in-python
        if False and 'content-encoding' in response.headers and \
                response.headers['content-encoding'].lower() == 'gzip':
            print 'gziped response'
            buffer = StringIO.StringIO()
            with gzip.GzipFile(fileobj=buffer, mode="w") as f:
                f.write(output)
            output = buffer.getvalue()

        # handle chunking
        # (thanks to https://gist.github.com/josiahcarlson/3250376)
        # although we only pretend to chunk and send it all at once!
        if 'transfer-encoding' in response.headers and \
                response.headers['transfer-encoding'].lower() == 'chunked':
            self.wfile.write('%X\r\n%s\r\n' %
                             (len(output), output))
            # send the chunked trailer
            self.wfile.write('0\r\n\r\n')
        else:
            self.wfile.write(output)
        self.log_response(response)

    def do_GET(self):
        print 'Got GET: ', self.path
        headers = rewrite_headers(self.headers)
        self.log_request()
        try:
            response = requests.get(self.path, headers=headers, timeout=15.0)
            self.respond(response)
        except:
            self.log_exception()
        self.log_flush()

    def do_POST(self):
        print 'Got POST: ', self.path
        headers = rewrite_headers(self.headers)
        self.data = self.rfile.read(int(self.headers['Content-Length']))
        self.log_request()
        try:
            response = requests.post(self.path, headers=headers, data=self.data, timeout=15.0)
            self.respond(response)
        except:
            self.log_exception()
        self.log_flush()

    def do_PUT(self):
        headers = rewrite_headers(self.headers)
        self.data = self.rfile.read(int(self.headers['Content-Length']))
        self.log_request()
        try:
            response = requests.put(self.path, headers=headers, data=self.data, timeout=15.0)
            self.respond(response)
        except:
            self.log_exception()
        self.log_flush()

    def log_exception(self):
        logstr = self._logstr if hasattr(self, '_logstr') else ''
        logstr += traceback.format_exc() + '\n'
        self._logstr = logstr

    def log_error(self, format, *args):
        pass

    def log_request(self, *args):
        logstr = self._logstr if hasattr(self, '_logstr') else ''

        logstr += "*** REQUEST ***\n"
        logstr += self.command + ' ' + self.path + '\n'
        for (k, v) in rewrite_headers(self.headers).items():
            logstr += "{0} = {1}\n".format(k, v)
        logstr += '\n'
        if self.command in ['POST', 'PUT']:
            logstr += self.data + '\n'
        logstr += "*** END REQUEST ***\n"

        self._logstr = logstr

    def log_response(self, response):
        logstr = self._logstr if hasattr(self, '_logstr') else ''

        logstr += "*** RESPONSE ***\n"
        if response.status_code in self.responses:
            shortmessage, longmessage = self.responses[response.status_code]
        else:
            shortmessage = longmessage = "Not a code known by requests module!"
        logstr += "{0} {1}\n".format(response.status_code, shortmessage)
        for (k, v) in rewrite_headers(response.headers).items():
            logstr += "{0} = {1}\n".format(k, v)
        logstr += '\n'
        logstr += response.content + '\n'
        logstr += "*** END RESPONSE ***\n"

        self._logstr = logstr

    def log_flush(self):
        logger = logging.getLogger('http proxy')
        if hasattr(self, '_logstr') and self._logstr is not None:
            logger.info(self._logstr)
