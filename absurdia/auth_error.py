
import absurdia
from absurdia.error import AbsurdiaError


class AuthError(AbsurdiaError):
    def __init__(
        self,
        code,
        description,
        http_body=None,
        http_status=None,
        json_body=None,
        headers=None,
    ):
        super(AuthError, self).__init__(
            description, http_body, http_status, json_body, headers, code
        )

    def construct_error_object(self):
        if self.json_body is None:
            return None

        return (
            absurdia.api_resources.error_object.AuthErrorObject.construct_from(
                self.json_body, absurdia.agent_token
            )
        )

class InvalidGrantError(AuthError):
    pass


class InvalidRequestError(AuthError):
    pass


class UnverifiedAccount(AuthError):
    pass


class SignatureRequired(AuthError):
    pass


class InvalidSignature(AuthError):
    pass

class SystemError(AuthError):
    pass