from __future__ import with_statement
import re
import os
import time
import sys
import urllib2
import shutil
from .exception import HTTPError
from pip.req import InstallRequirement
from pip.index import PackageFinder, Link
from pip.log import logger
from errno import EEXIST

PYPI_URL_PREFIX = 'http://pypi.python.org'
PYPI_URL = '%s/simple' % PYPI_URL_PREFIX
DEFAULT_CACHE_DIR = os.getenv('PIPP_CACHE_DIR', '/tmp/pipproxy')
DEFAULT_PKG_INDEX_TIMEOUT = int(os.getenv('PIPP_PKG_INDEX_TIMEOUT', str(60*60*24*3)))
HTML_CTYPE_HEADER = ('Content-type', 'text/html')

ARCHIVE_EXTENSIONS = ('tar', 'tar.gz', 'tar.bz2', 'tgz', 'zip')
ARCHIVE_EXTENSIONS_RE_FRAGMENT = '|'.join(ext.replace('.', '\\.') for ext in ARCHIVE_EXTENSIONS)


logger.consumers.extend([(0, sys.stderr)])

class IndexExpired(Exception):
    pass

def headers_list_set_default(hlist, header, value):
    """ given a list of headers in the form of header-value tuples,
    add the given ``header`` with the given ``value`` to the list if
    it is not found. Searching is done in a case-insensitive manner. """
    for h, _ in hlist:
        if h.lower() == header.lower():
            # found
            return
    hlist.append((header, value))


def parse_link_url(url):
    url, _, fragment = url.partition('#')
    url, _, query = url.partition('?')
    name = url[url.rindex('/')+1:]
    return name, url, fragment


def alt_filename(fname, seen_names):
    if fname not in seen_names:
        seen_names.add(fname)
        return fname

    fname_stem = fname
    fname_ext = ''
    i = 1
    for e in ARCHIVE_EXTENSIONS:
        if fname.endswith(".%s" % e):
            fname_stem = fname[:-len(e)-1]
            fname_ext = e
            break

    if '__pp' in fname_stem:
        fname_stem, _, i = fname_stem.partition('__pp')
        i = int(i) + 1

    while i < 100:
        fname = "%s__pp%d.%s" % (fname_stem, i, fname_ext)
        if fname not in seen_names:
            break
        i += 1

    return fname



def fetch_generate_page(dir, package):
    finder = PackageFinder([], []) # these args are not really used
    req = InstallRequirement(package, None)
    page_versions = []
    out_html = []

    for p in finder._get_pages([Link("%s/%s" % (PYPI_URL, package))], req):
        page_versions.extend(finder._package_versions(p.links, req.name.lower()))

    if not page_versions:
        # nothing found - maybe no such package
        return ''

    seen_archive_names = set()
    for _parsed_version, link, version in page_versions:
        archive_name, real_url, fragment = parse_link_url(link.url)
        archive_name = alt_filename(archive_name, seen_archive_names)
        with open("%s/%s.url" % (dir, archive_name), "w") as f:
            f.write(real_url)

        if fragment:
            fragment = "#%s" % fragment
        out_html.append('<a href="%s%s">%s</a>' % (archive_name, fragment, version))

    return "<html><head><title>Links for %s</title></head><body><h1>Links for %s</h1>%s</body></html>" % (
        package,
        package,
        '\n'.join(out_html))
    

def cached_fetch_index(dir, package, index_timeout):
    filename = "%s/index.html" % dir
    try:
        with open(filename) as f:
            st = os.fstat(f.fileno()) # XXX: portable?
            if st.st_mtime + index_timeout < time.time():
                raise IndexExpired()
            return f.read()
    except (IOError, OSError, IndexExpired):
        _makedirs(dir)
        url = "%s/%s" % (PYPI_URL, package)
        print >> sys.stderr, "fetching %s" % url
        html = fetch_generate_page(dir, package)
        if not html:
            # not found
            return html
        with open(filename, "w") as f:
            f.write(html)
        return html


def _makedirs(d):
    try:
        os.makedirs(d)
    except OSError, e:
        if e.errno == EEXIST:
            return
        raise

def serve_package_noslash(env, package):
    raise HTTPError(302, 'moved', [('Location', 'http://%s/simple/%s/' % (env['HTTP_HOST'], package))])


def serve_package(env, package, version=None):
    index_timeout = int(env.get('PIPP_PKG_INDEX_TIMEOUT', DEFAULT_PKG_INDEX_TIMEOUT))
    cachedir = env.get('PIPP_CACHE_DIR', DEFAULT_CACHE_DIR)
    return ([HTML_CTYPE_HEADER],
            [cached_fetch_index("%s/%s" % (cachedir, package), package, index_timeout)])


def serve_download(env, package, file):
    # XXX: guard against race condition causing concurrent downloads of the same file
    filename = "%s/%s/%s" % (env.get('PIPP_CACHE_DIR', DEFAULT_CACHE_DIR), package, file)
    try:
        f = open(filename)
        return ([('Content-type', 'application/octet-stream')], f)
    except (IOError, OSError), e:
        with open("%s.url" % filename) as urlf:
            url = urlf.read()

        try:
            r = urllib2.urlopen(url)
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise HTTPError(404, 'Not found')

        with open(filename, "w") as f:
            shutil.copyfileobj(r, f)

        return serve_download(env, package, file)


URLS = (
    (re.compile(r'^/simple/(?P<package>\w+[\w.\-]+)$'), serve_package_noslash),
    (re.compile(r'^/simple/(?P<package>\w+[\w.\-]+)/$'), serve_package),
    # extension may not be present (most github hosted stuff e.g. "dumbo" module)
    (re.compile(r'^/simple/(?P<package>\w+[\w.\-]+)/(?P<file>\w+[\w.\-]+(\.(%s))?)$' % ARCHIVE_EXTENSIONS_RE_FRAGMENT),
     serve_download),
)
def route(environ):
    for pattern, handler in URLS:
        m = pattern.match(environ['PATH_INFO'])
        if m:
            return handler(environ, **m.groupdict())
    raise HTTPError(404, 'Not found')


def proxy(environ, start_response):
    status = '200 OK'
    try:
        headers, content = route(environ)
    except HTTPError, e:
        status = str(e)
        headers = e.headers
        content = [e.body]

    #found = False
    #for e in environ:
    #    if e.startswith("PIPP"):
    #        print >> sys.stderr, "%s => %s" % (e, environ[e])
    #        found = True
    #        break

    #for e in os.environ:
    #    if e.startswith("PIPP"):
    #        print >> sys.stderr, "%s => %s" % (e, os.environ[e])
    #        found = True
    #        break

    #if not found:
    #    print >> sys.stderr, "NOT FOUND!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

    headers_list_set_default(headers, 'content-type', 'text/html')
    start_response(status, headers)
    return content
