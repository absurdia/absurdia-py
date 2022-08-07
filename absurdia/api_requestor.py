import calendar
import datetime
import json
import platform
import time
from urllib.parse import urlencode, urlsplit, urlunsplit
import uuid
import warnings
from collections import OrderedDict

import absurdia
from absurdia import error, auth_error, http_client, version, util
from absurdia.absurdia_response import AbsurdiaResponse, AbsurdiaStreamResponse


def _encode_datetime(dttime):
    if dttime.tzinfo and dttime.tzinfo.utcoffset(dttime) is not None:
        utc_timestamp = calendar.timegm(dttime.utctimetuple())
    else:
        utc_timestamp = time.mktime(dttime.timetuple())

    return int(utc_timestamp)


def _encode_nested_dict(key, data, fmt="%s[%s]"):
    d = OrderedDict()
    for subkey, subvalue in data.items():
        d[fmt % (key, subkey)] = subvalue
    return d


def _api_encode(data):
    for key, value in data.items():
        key = util.utf8(key)
        if value is None:
            continue
        elif isinstance(value, list) or isinstance(value, tuple):
            for i, sv in enumerate(value):
                if isinstance(sv, dict):
                    subdict = _encode_nested_dict("%s[%d]" % (key, i), sv)
                    for k, v in _api_encode(subdict):
                        yield (k, v)
                else:
                    yield ("%s[%d]" % (key, i), util.utf8(sv))
        elif isinstance(value, dict):
            subdict = _encode_nested_dict(key, value)
            for subkey, subvalue in _api_encode(subdict):
                yield (subkey, subvalue)
        elif isinstance(value, datetime.datetime):
            yield (key, _encode_datetime(value))
        else:
            yield (key, util.utf8(value))


def _build_api_url(url, query):
    scheme, netloc, path, base_query, fragment = urlsplit(url)

    if base_query:
        query = "%s&%s" % (base_query, query)

    return urlunsplit((scheme, netloc, path, query, fragment))


class APIRequestor(object):
    def __init__(
        self,
        token=None,
        signature_key=None,
        client=None,
        api_base=None,
        api_version=None,
        account=None,
    ):
        self.api_base = api_base or absurdia.api_base
        self.agent_token = token
        self.agent_signature_key = signature_key
        self.api_version = api_version or absurdia.api_version
        self.absurdia_account = account

        if self.agent_token is None or self.agent_signature_key is None:
            util.load_agent()
        if self.agent_token is None:
            self.agent_token = absurdia.agent_token
        if self.agent_signature_key is None:
            self.agent_signature_key = absurdia.agent_signature_key

        self._default_proxy = None

        from absurdia import verify_ssl_certs as verify
        from absurdia import proxy

        if client:
            self._client = client
        elif absurdia.default_http_client:
            self._client = absurdia.default_http_client
            if proxy != self._default_proxy:
                warnings.warn(
                    "absurdia.proxy was updated after sending a "
                    "request - this is a no-op. To use a different proxy, "
                    "set absurdia.default_http_client to a new client "
                    "configured with the proxy."
                )
        else:
            # If the absurdia.default_http_client has not been set by the user
            # yet, we'll set it here. This way, we aren't creating a new
            # HttpClient for every request.
            absurdia.default_http_client = http_client.new_default_http_client(
                verify_ssl_certs=verify, proxy=proxy
            )
            self._client = absurdia.default_http_client
            self._default_proxy = proxy

    @classmethod
    def format_app_info(cls, info):
        str = info["name"]
        if info["version"]:
            str += "/%s" % (info["version"],)
        if info["url"]:
            str += " (%s)" % (info["url"],)
        return str

    def request(self, method, url, params=None, headers=None, body=None):
        rbody, rcode, rheaders, _ = self.request_raw(
            method.lower(), url, params, headers, body
        )
        resp = self.interpret_response(rbody, rcode, rheaders)
        return resp

    def handle_error_response(self, rbody, rcode, resp, rheaders):
        try:
            error_data = resp["error"]
        except (KeyError, TypeError):
            raise error.APIError(
                "Invalid response object from API: %r (HTTP response code "
                "was %d)" % (rbody, rcode),
                rbody,
                rcode,
                resp,
            )
            
        err = self.specific_api_error(
                rbody, rcode, resp, rheaders, error_data
            )

        raise err

    def specific_api_error(self, rbody, rcode, resp, rheaders, error_data):
        util.log_info(
            "Absurdia API error received",
            error_code=error_data.get("code"),
            error_type=error_data.get("error"),
            error_message=error_data,
            error_param=error_data.get("detail"),
        )

        # Rate limits were previously coded as 400's with code 'rate_limit'
        if rcode == 429:
            return error.RateLimitError(
                error_data.get("message"), rbody, rcode, resp, rheaders
            )
        elif rcode in [400, 404]:
            if error_data.get("type") == "idempotency_error":
                return error.IdempotencyError(
                    error_data.get("message"), rbody, rcode, resp, rheaders
                )
            else:
                return error.InvalidRequestError(
                    error_data.get("message"),
                    error_data.get("param"),
                    error_data.get("code"),
                    rbody,
                    rcode,
                    resp,
                    rheaders,
                )
        elif rcode == 401:
            return error.AuthenticationError(
                error_data.get("message"), rbody, rcode, resp, rheaders
            )
        elif rcode == 402:
            return error.CardError(
                error_data.get("message"),
                error_data.get("param"),
                error_data.get("code"),
                rbody,
                rcode,
                resp,
                rheaders,
            )
        elif rcode == 403:
            return error.PermissionError(
                error_data.get("message"), rbody, rcode, resp, rheaders
            )
        else:
            return error.APIError(
                error_data.get("message"), rbody, rcode, resp, rheaders
            )

    def specific_auth_error(self, rbody, rcode, resp, rheaders, error_code):
        description = resp.get("error_description", error_code)

        util.log_info(
            "Absurdia Auth error received",
            error_code=error_code,
            error_description=description,
        )

        args = [error_code, description, rbody, rcode, resp, rheaders]

        if error_code == "invalid_grant":
            return auth_error.InvalidGrantError(*args)
        elif error_code == "invalid_request":
            return auth_error.InvalidRequestError(*args)
        elif error_code == "unverified_account":
            return auth_error.UnverifiedAccount(*args)
        elif error_code == "signature_required":
            return auth_error.SignatureRequired(*args)
        elif error_code == "invalid_signature":
            return auth_error.InvalidSignature(*args)
        elif error_code == "system_error":
            return auth_error.SystemError(*args)
        return None

    def request_headers(self, agent_token, method, payload=None):
        user_agent = "Absurdia/v1 PythonBindings/%s" % (version.VERSION,)
        if absurdia.app_info:
            user_agent += " " + self.format_app_info(absurdia.app_info)

        ua = {
            "bindings_version": version.VERSION,
            "lang": "python",
            "publisher": "absurdia",
            "httplib": self._client.name,
        }
        for attr, func in [
            ["lang_version", platform.python_version],
            ["platform", platform.platform],
            ["uname", lambda: " ".join(platform.uname())],
        ]:
            try:
                val = func()
            except Exception:
                val = "(disabled)"
            ua[attr] = val
        if absurdia.app_info:
            ua["application"] = absurdia.app_info

        headers = {
            "Abs-Client-User-Agent": json.dumps(ua),
            "User-Agent": user_agent,
            "Authorization": "Bearer %s" % (agent_token,),
            "Content-Type": "application/json",
            "Accept-Encoding": "br,gzip",
        }

        if method == "post" or method == "patch":
            headers.setdefault("Idempotency-Key", str(uuid.uuid4()))
            
        if method != "get" and payload:
            headers.setdefault("Abs-Signature", util.sign(payload))

        if self.api_version is not None:
            headers["Absurdia-Version"] = self.api_version

        return headers

    def request_raw(
        self,
        method,
        url,
        params=None,
        supplied_headers=None,
        body=None,
    ):
        """
        Mechanism for issuing an API call
        """

        if self.agent_token:
            bearer = self.agent_token
        else:
            from absurdia import agent_token

            bearer = agent_token

        if bearer is None:
            raise error.AuthenticationError(
                "No agent key provided. (HINT: set your agent key using "
                '"absurdia.agent_token = <AGENT-KEY>"). You can generate agent keys '
                "from the Absurdia web interface.  See https://app.absurdia.markets/dash/agents "
                "for details, or email support@absurdia.eu if you have any "
                "questions."
            )

        abs_url = "%s%s" % (self.api_base, url)

        #encoded_params = urlencode(list(_api_encode(params or {})))

        # Don't use strict form encoding by changing the square bracket control
        # characters back to their literals. This is fine by the server, and
        # makes these parameter strings easier to read.
        #encoded_params = encoded_params.replace("%5B", "[").replace("%5D", "]")

        if method in ["get", "post", "patch", "put", "delete"]:
            #post_data = encoded_params                
            body = params
        else:
            raise error.APIConnectionError(
                "Unrecognized HTTP method %r.  This may indicate a bug in the "
                "Absurdia bindings.  Please contact support@absurdia.markets for "
                "assistance." % (method,)
            )

        headers = self.request_headers(bearer, method, payload=body)
        if supplied_headers is not None:
            for key, value in supplied_headers:
                headers[key] = value

        util.log_info("Request to Absurdia API", method=method, path=abs_url)
        util.log_debug(
            "Post details",
            body=body,
            api_version=self.api_version,
        )
        rcontent, rcode, rheaders = self._client.request_with_retries(
                method, abs_url, headers, body=body
            )

        util.log_info("Absurdia API response", path=abs_url, response_code=rcode)
        util.log_debug("API response body", body=str(rcontent))

        return rcontent, rcode, rheaders, bearer

    def _should_handle_code_as_error(self, rcode):
        return not 200 <= rcode < 300

    def interpret_response(self, rbody, rcode, rheaders):
        try:
            if hasattr(rbody, "decode"):
                rbody = rbody.decode("utf-8")
            resp = AbsurdiaResponse(rbody, rcode, rheaders)
        except Exception:
            raise error.APIError(
                "Invalid response body from API: %s "
                "(HTTP response code was %d)" % (rbody, rcode),
                rbody,
                rcode,
                rheaders,
            )
        if self._should_handle_code_as_error(rcode):
            self.handle_error_response(rbody, rcode, resp.body, rheaders)
        return resp
 