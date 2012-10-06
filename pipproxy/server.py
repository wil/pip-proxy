from __future__ import absolute_import
import sys
from wsgiref.simple_server import make_server
from pipproxy.app import proxy


def runit(port):
    httpd = make_server('', port, proxy)
    print "Serving HTTP on port %d..." % port

    # Respond to requests until process is killed
    httpd.serve_forever()

    # Alternative: serve one request, then exit
    httpd.handle_request()


if __name__ == '__main__':
    port = 8008
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    runit(port)
