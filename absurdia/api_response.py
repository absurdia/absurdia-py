import json

class APIResponse():
    def __init__(self, status_code: int, text: str, headers=None):
        self.content = text
        self.headers = headers
        self.cached = False
        self.status_code = status_code
        self.ok = self.status_code < 400

    @property
    def text(self):
        return self.content
    
    @property
    def json(self):
        return json.loads(self.content)
    
    @property
    def request_id(self):
        try:
            return self.headers["x-request-id"]
        except KeyError:
            return None
    
    @property
    def idempotency_key(self):
        try:
            return self.headers["idempotency-key"]
        except KeyError:
            return None

    def __repr__(self):
        return 'HTTP {} {} {}'.format(self.status_code, self.content, self.request_id)