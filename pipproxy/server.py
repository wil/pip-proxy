from __future__ import absolute_import
from wsgiref.simple_server import make_server
from pipproxy.app import proxy

port = 8008
httpd = make_server('', port, proxy)
print "Serving HTTP on port %d..." % port

# Respond to requests until process is killed
httpd.serve_forever()

# Alternative: serve one request, then exit
httpd.handle_request()

