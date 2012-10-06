
PIP Proxy (pipproxy) is a WSGI Server that acts as a front end for PIP that
caches PyPI index and tarballs.

This is not just a simple PyPI index cache. It caches the result of all
versions that pip finds, including those hosted outside of PyPI.


Prerequisites
-------------

``pip`` 1.0 or higher is required.

Check using:

    pip --version

Upgrade using:

    pip install --upgrade pip


Quick Start
-----------

To run the wsgi server, run:

    mkdir /tmp/pip_proxy_cache
    PIPP_CACHE_DIR=/tmp/pip_proxy_cache python pipproxy/server.py 8008

To use it for all your pip installs:

    export PIP_INDEX_URL=http://localhost:8008/simple
    pip install foobar-package


Using other web servers
-----------------------

Just use the pipproxy.wsgi module. For example, to use it with gunicorn:

    PIPP_CACHE_DIR=/tmp/pip_proxy_cache \
      gunicorn -b 127.0.0.1:8008 --timeout=600 pipproxy.wsgi



TODO
----

* optimize caching of package index: do not refresh at ``/simple/<package_name>/``
  but only do so at ``/simple/<package_name>/<version>`` if version is not found
* potential race condition of two clients requesting the same package or
  distribution file that is not cached
* for distribution files that are not yet cached, stream them to client while
  it is being downloaded
