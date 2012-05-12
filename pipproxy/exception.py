
class HTTPError(Exception):
    def __init__(self, code, msg, headers=None, body=''):
        self.code = code
        self.msg = msg
        self.headers = headers or []
        self.body = body

    def __str__(self):
        return '%s %s' % (self.code, self.msg)
