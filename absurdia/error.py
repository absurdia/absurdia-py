import absurdia

class AbsurdiaError(Exception):
    def __init__(
        self,
        message=None,
        http_body=None,
        http_status=None,
        json_body=None,
        headers=None,
        code=None,
    ):
        super(AbsurdiaError, self).__init__(message)

        if http_body and hasattr(http_body, "decode"):
            try:
                http_body = http_body.decode("utf-8")
            except BaseException:
                http_body = (
                    "<Could not decode body as utf-8. "
                    "Please report to support@absurdia.markets>"
                )

        self._message = message
        self.http_body = http_body
        self.http_status = http_status
        self.json_body = json_body
        self.headers = headers or {}
        self.code = code
        self.request_id = self.headers.get("x-request-id", None)

    def __str__(self):
        msg = self._message or "<empty message>"
        if self.request_id is not None:
            return u"Request {0}: {1}".format(self.request_id, msg)
        else:
            return msg

    # Returns the underlying `Exception` (base class) message, which is usually
    # the raw message returned by Absurdia's API. This was previously available
    # in python2 via `error.message`. Unlike `str(error)`, it omits "Request
    # req_..." from the beginning of the string.
    @property
    def user_message(self):
        return self._message

    def __repr__(self):
        return "%s(message=%r, http_status=%r, request_id=%r)" % (
            self.__class__.__name__,
            self._message,
            self.http_status,
            self.request_id,
        )


class APIError(AbsurdiaError):
    pass


class APIConnectionError(AbsurdiaError):
    def __init__(
        self,
        message,
        http_body=None,
        http_status=None,
        json_body=None,
        headers=None,
        code=None,
        should_retry=False,
    ):
        super(APIConnectionError, self).__init__(
            message, http_body, http_status, json_body, headers, code
        )
        self.should_retry = should_retry


class AbsurdiaErrorWithParamCode(AbsurdiaError):
    def __repr__(self):
        return (
            "%s(message=%r, param=%r, code=%r, http_status=%r, "
            "request_id=%r)"
            % (
                self.__class__.__name__,
                self._message,
                self.param,
                self.code,
                self.http_status,
                self.request_id,
            )
        )


class IdempotencyError(AbsurdiaError):
    pass


class InvalidRequestError(AbsurdiaErrorWithParamCode):
    def __init__(
        self,
        message,
        param,
        code=None,
        http_body=None,
        http_status=None,
        json_body=None,
        headers=None,
    ):
        super(InvalidRequestError, self).__init__(
            message, http_body, http_status, json_body, headers, code
        )
        self.param = param


class AuthenticationError(AbsurdiaError):
    pass


class PermissionError(AbsurdiaError):
    pass


class RateLimitError(AbsurdiaError):
    pass


class SignatureVerificationError(AbsurdiaError):
    def __init__(self, message, sig_header, http_body=None):
        super(SignatureVerificationError, self).__init__(message, http_body)
        self.sig_header = sig_header