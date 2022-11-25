import json

class APIError(Exception):
    def __init__(
        self,
        message=None,
        http_status=None,
        headers=None
    ):
        super().__init__(message)

        if message and hasattr(message, "decode"):
            try:
                message = message.decode("utf-8")
            except BaseException:
                message = (
                    "<Could not decode message as utf-8. "
                    "Please report to support@absurdia.markets>"
                )

        self._message = message
        self.http_status = http_status
        self.headers = headers or {}
        self.request_id = self.headers.get("x-request-id", None)
        
        self.json_body = None
        if self.headers.get("content-type", None):
            if "application/json" in self.headers["content-type"]:
                try:
                    self.json_body = json.loads(self._message)
                except BaseException:
                    pass

        self.code = None
        if self.json_body:
            self.code = self.json_body.get("code", None)

    def __str__(self):
        if self.request_id is not None:
            return u"Request {0}: {1}".format(self.request_id, self._message or "<empty>")
        else:
            return self._message

    # Returns the underlying `Exception` (base class) message, which is usually
    # the raw message returned by Absurdia's API.
    @property
    def message(self):
        return self._message
    
    @property
    def json(self):
        return self.json_body
    
    @property
    def status_code(self):
        return self.http_status
    
    @property
    def code(self):
        return self.code

    def __repr__(self):
        return "%s(message=%r, http_status=%r, request_id=%r)" % (
            self.__class__.__name__,
            self.message,
            self.status_code,
            self.request_id,
        )
        
class AuthenticationError(APIError):
    pass