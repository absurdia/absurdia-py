import json
from collections import OrderedDict

class AbsurdiaResponseBase(object):
    def __init__(self, code, headers):
        self.code = code
        self.headers = headers

    @property
    def idempotency_key(self):
        try:
            return self.headers["idempotency-key"]
        except KeyError:
            return None

    @property
    def request_id(self):
        try:
            return self.headers["x-request-id"]
        except KeyError:
            return None


class AbsurdiaResponse(AbsurdiaResponseBase):
    def __init__(self, body, code, headers):
        AbsurdiaResponseBase.__init__(self, code, headers)
        self.body = body
        self.data = json.loads(body)
        if code == 200 or code == 201:
            self.data = self.data['data']

class AbsurdiaStreamResponse(AbsurdiaResponseBase):
    def __init__(self, io, code, headers):
        AbsurdiaResponseBase.__init__(self, code, headers)
        self.io = io