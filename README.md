PIP Proxy (pipproxy) is a WSGI Server that acts as a front end for PIP that caches PyPI index and tarballs.


TODO
----
* optimize caching of package index: do not refresh at /simple/<package_name>/ but only do so at /simple/<package_name>/<version> if version is not found
* potential race condition of two clients requesting the same package or distribution file that is not cached
* for distribution files that are not yet cached, stream them to client while it is being downloaded
