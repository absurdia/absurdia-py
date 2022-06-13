import sys
import textwrap
import ssl
import time
import random
import threading
import json

import absurdia
import absurdia.util as util
import absurdia.error as error

try:
    import httpx
    version = httpx.__version__
    major, minor, patch = [int(i) for i in version.split(".")]
    if (major, minor, patch) < (0, 21, 2):
        sys.stderr.write(
            "Warning: the Absurdia library requires that your Python "
            '"httpx" library be newer than version 0.21.2, but your '
            '"httpx" library is version %s. Absurdia will fall back to '
            'the alternate HTTP library "requests" so everything should work. We '
            'recommend upgrading your "httpx" library. If you have any '
            "questions, please contact support@absurdia.eu. (HINT: running "
            '"pip install -U httpx" should upgrade your httpx '
            "library to the latest version.)" % (version,)
        )
        httpx = None
except ImportError:
    httpx = None
    try:
        import requests
    except ImportError:
        requests = None

def _now_ms():
    return int(round(time.time() * 1000))

def new_default_http_client(*args, **kwargs):
    if httpx:
        impl = HttpxClient
    elif requests:
        impl = RequestsClient
    else:
        sys.stderr.write(
            "Error: the Absurdia library requires that the Python "
            '"httpx" or "requests" library be installed in your environment, but none '
            'was found. Run "pip install httpx" tp install the preferred HTTP client. '
            "If you have any questions, please contact support@absurdia.eu."
        )
        raise ImportError("Missing dependency: httpx or requests")

    return impl(*args, **kwargs)

class RequestMetrics(object):
    def __init__(self, request_id, request_duration_ms):
        self.request_id = request_id
        self.request_duration_ms = request_duration_ms

    def payload(self):
        return {
            "request_id": self.request_id,
            "request_duration_ms": self.request_duration_ms,
        }


class HTTPClient(object):
    MAX_DELAY = 2
    INITIAL_DELAY = 0.5
    MAX_RETRY_AFTER = 60

    def __init__(self, verify_ssl_certs=True, proxy=None):
        self._verify_ssl_certs = verify_ssl_certs
        if proxy:
            if isinstance(proxy, str):
                proxy = {"http": proxy, "https": proxy}
            if not isinstance(proxy, dict):
                raise ValueError(
                    "Proxy(ies) must be specified as either a string "
                    "URL or a dict() with string URL under the"
                    " "
                    "https"
                    " and/or "
                    "http"
                    " keys."
                )
        self._proxy = proxy.copy() if proxy else None

        self._thread_local = threading.local()

    def request_with_retries(self, method, url, headers, params=None, body=None):
        return self._request_with_retries_internal(
            method, url, params, headers, body, is_streaming=False
        )

    def request_stream_with_retries(
        self, method, url, headers, post_data=None
    ):
        return self._request_with_retries_internal(
            method, url, headers, post_data, is_streaming=True
        )

    def _request_with_retries_internal(
        self, method, url, params, headers, body, is_streaming
    ):
        self._add_telemetry_header(headers)

        num_retries = 0

        while True:
            request_start = _now_ms()

            try:
                if is_streaming:
                    response = self.request_stream(
                        method, url, params, headers, body
                    )
                else:
                    response = self.request(method, url, params, headers, body)
                connection_error = None
            except error.APIConnectionError as e:
                connection_error = e
                response = None

            if self._should_retry(response, connection_error, num_retries):
                if connection_error:
                    util.log_info(
                        "Encountered a retryable error %s"
                        % connection_error.user_message
                    )
                num_retries += 1
                sleep_time = self._sleep_time_seconds(num_retries, response)
                util.log_info(
                    (
                        "Initiating retry %i for request %s %s after "
                        "sleeping %.2f seconds."
                        % (num_retries, method, url, sleep_time)
                    )
                )
                time.sleep(sleep_time)
            else:
                if response is not None:
                    self._record_request_metrics(response, request_start)

                    return response
                else:
                    raise connection_error

    def request(self, method, url, headers, post_data=None):
        raise NotImplementedError(
            "HTTPClient subclasses must implement `request`"
        )

    def request_stream(self, method, url, headers, post_data=None):
        raise NotImplementedError(
            "HTTPClient subclasses must implement `request_stream`"
        )

    def _should_retry(self, response, api_connection_error, num_retries):
        if num_retries >= self._max_network_retries():
            return False

        if response is None:
            # We generally want to retry on timeout and connection
            # exceptions, but defer this decision to underlying subclass
            # implementations. They should evaluate the driver-specific
            # errors worthy of retries, and set flag on the error returned.
            return api_connection_error.should_retry

        _, status_code, rheaders = response

        # The API may ask us not to retry (eg; if doing so would be a no-op)
        # or advise us to retry (eg; in cases of lock timeouts); we defer to that.
        #
        # Note that we expect the headers object to be a CaseInsensitiveDict, as is the case with the requests library.
        if rheaders is not None and "abs-should-retry" in rheaders:
            if rheaders["abs-should-retry"] == "false":
                return False
            if rheaders["abs-should-retry"] == "true":
                return True

        # Retry on conflict errors.
        if status_code == 409:
            return True

        # Retry on 500, 503, and other internal errors.
        #
        # Note that we expect the abs-should-retry header to be false
        # in most cases when a 500 is returned, since our idempotency framework
        # would typically replay it anyway.
        if status_code >= 500:
            return True

        return False

    def _max_network_retries(self):
        from absurdia import max_network_retries

        # Configured retries, isolated here for tests
        return max_network_retries

    def _retry_after_header(self, response=None):
        if response is None:
            return None
        _, _, rheaders = response

        try:
            return int(rheaders["retry-after"])
        except (KeyError, ValueError):
            return None

    def _sleep_time_seconds(self, num_retries, response=None):
        # Apply exponential backoff with initial_network_retry_delay on the
        # number of num_retries so far as inputs.
        # Do not allow the number to exceed max_network_retry_delay.
        sleep_seconds = min(
            HTTPClient.INITIAL_DELAY * (2 ** (num_retries - 1)),
            HTTPClient.MAX_DELAY,
        )

        sleep_seconds = self._add_jitter_time(sleep_seconds)

        # But never sleep less than the base sleep seconds.
        sleep_seconds = max(HTTPClient.INITIAL_DELAY, sleep_seconds)

        # And never sleep less than the time the API asks us to wait, assuming it's a reasonable ask.
        retry_after = self._retry_after_header(response) or 0
        if retry_after <= HTTPClient.MAX_RETRY_AFTER:
            sleep_seconds = max(retry_after, sleep_seconds)

        return sleep_seconds

    def _add_jitter_time(self, sleep_seconds):
        # Randomize the value in [(sleep_seconds/ 2) to (sleep_seconds)]
        # Also separated method here to isolate randomness for tests
        sleep_seconds *= 0.5 * (1 + random.uniform(0, 1))
        return sleep_seconds

    def _add_telemetry_header(self, headers):
        last_request_metrics = getattr(
            self._thread_local, "last_request_metrics", None
        )
        if absurdia.enable_telemetry and last_request_metrics:
            telemetry = {
                "last_request_metrics": last_request_metrics.payload()
            }
            headers["Abs-Client-Telemetry"] = json.dumps(telemetry)

    def _record_request_metrics(self, response, request_start):
        _, _, rheaders = response
        if "Abs-Request-Id" in rheaders and absurdia.enable_telemetry:
            request_id = rheaders["Abs-Request-Id"]
            request_duration_ms = _now_ms() - request_start
            self._thread_local.last_request_metrics = RequestMetrics(
                request_id, request_duration_ms
            )

    def close(self):
        raise NotImplementedError(
            "HTTPClient subclasses must implement `close`"
        )

class HttpxClient(HTTPClient):
    name = "httpx"

    def __init__(self, timeout=80, session=None, **kwargs):
        super(HttpxClient, self).__init__(**kwargs)
        self._session = session
        self._timeout = timeout

    def request(self, method, url, headers, params, body=None):
        return self._request_internal(
            method, url, params, headers, body, is_streaming=False
        )

    def _request_internal(self, method, url, headers, params, body, is_streaming):
        kwargs = {}
        if self._proxy:
            kwargs["proxies"] = self._proxy

        if is_streaming:
            kwargs["stream"] = True

        if getattr(self._thread_local, "session", None) is None:
            self._thread_local.session = self._session or httpx.Client(http2=True)

        try:
            try:
                result = self._thread_local.session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=body,
                    timeout=self._timeout,
                    **kwargs
                )
            except TypeError as e:
                raise TypeError(
                    "Warning: It looks like your installed version of the "
                    '"httpx" library is not compatible with Absurdia\'s '
                    "usage thereof. (HINT: The most likely cause is that "
                    'your "httpx" library is out of date. You can fix '
                    'that by running "pip install -U httpx".) The '
                    "underlying error was: %s" % (e,)
                )

            if is_streaming:
                content = result.raw
            else:
                # This causes the content to actually be read, which could cause
                # e.g. a socket timeout. TODO: The other fetch methods probably
                # are susceptible to the same and should be updated.
                content = result.content

            status_code = result.status_code
        except Exception as e:
            # Would catch just requests.exceptions.RequestException, but can
            # also raise ValueError, RuntimeError, etc.
            self._handle_request_error(e)
        return content, status_code, result.headers

    def _handle_request_error(self, e):

        # Catch SSL error first as it belongs to ConnectionError,
        # but we don't want to retry
        if isinstance(e, ssl.SSLCertVerificationError):
            msg = (
                "Could not verify Absurdia's SSL certificate.  Please make "
                "sure that your network is not intercepting certificates.  "
                "If this problem persists, let us know at "
                "support@absurdia.eu."
            )
            err = "%s: %s" % (type(e).__name__, str(e))
            should_retry = False
        # Retry only timeout and connect errors; similar to urllib3 Retry
        elif isinstance(
            e,
            (httpx.Client, httpx.ConnectError),
        ):
            msg = (
                "Unexpected error communicating with Absurdia.  "
                "If this problem persists, let us know at "
                "support@absurdia.eu."
            )
            err = "%s: %s" % (type(e).__name__, str(e))
            should_retry = True
        # Catch remaining request exceptions
        elif isinstance(e, httpx.ConnectError):
            msg = (
                "Unexpected error communicating with Absurdia.  "
                "If this problem persists, let us know at "
                "support@absurdia.eu."
            )
            err = "%s: %s" % (type(e).__name__, str(e))
            should_retry = False
        else:
            msg = (
                "Unexpected error communicating with Absurdia. "
                "It looks like there's probably a configuration "
                "issue locally.  If this problem persists, let us "
                "know at support@absurdia.eu."
            )
            err = "A %s was raised" % (type(e).__name__,)
            if str(e):
                err += " with error message %s" % (str(e),)
            else:
                err += " with no error message"
            should_retry = False

        msg = textwrap.fill(msg) + "\n\n(Network error: %s)" % (err,)
        raise error.APIConnectionError(msg, should_retry=should_retry)

    def close(self):
        if getattr(self._thread_local, "session", None) is not None:
            self._thread_local.session.close()

class RequestsClient(HTTPClient):
    name = "requests"

    def __init__(self, timeout=80, session=None, **kwargs):
        super(RequestsClient, self).__init__(**kwargs)
        self._session = session
        self._timeout = timeout

    def request(self, method, url, headers, params=None, body=None):
        return self._request_internal(
            method, url, params, headers, body, is_streaming=False
        )

    def _request_internal(self, method, url, params, headers, body, is_streaming):
        kwargs = {}
        if self._verify_ssl_certs:
            kwargs["verify"] = absurdia.ca_bundle_path
        else:
            kwargs["verify"] = False

        if self._proxy:
            kwargs["proxies"] = self._proxy

        if is_streaming:
            kwargs["stream"] = True

        if getattr(self._thread_local, "session", None) is None:
            self._thread_local.session = self._session or requests.Session()

        try:
            try:
                util.log_debug("Request: %s %s %s" % (method, url, headers))
                result = self._thread_local.session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=body,
                    timeout=self._timeout,
                    **kwargs
                )
            except TypeError as e:
                raise TypeError(
                    "Warning: It looks like your installed version of the "
                    '"requests" library is not compatible with Absurdia\'s '
                    "usage thereof. (HINT: The most likely cause is that "
                    'your "requests" library is out of date. You can fix '
                    'that by running "pip install -U requests".) The '
                    "underlying error was: %s" % (e,)
                )

            if is_streaming:
                content = result.raw
            else:
                # This causes the content to actually be read, which could cause
                # e.g. a socket timeout. TODO: The other fetch methods probably
                # are susceptible to the same and should be updated.
                content = result.content

            status_code = result.status_code
        except Exception as e:
            # Would catch just requests.exceptions.RequestException, but can
            # also raise ValueError, RuntimeError, etc.
            self._handle_request_error(e)
        return content, status_code, result.headers

    def _handle_request_error(self, e):

        # Catch SSL error first as it belongs to ConnectionError,
        # but we don't want to retry
        if isinstance(e, requests.exceptions.SSLError):
            msg = (
                "Could not verify Absurdia's SSL certificate.  Please make "
                "sure that your network is not intercepting certificates.  "
                "If this problem persists, let us know at "
                "support@absurdia.eu."
            )
            err = "%s: %s" % (type(e).__name__, str(e))
            should_retry = False
        # Retry only timeout and connect errors; similar to urllib3 Retry
        elif isinstance(
            e,
            (requests.exceptions.Timeout, requests.exceptions.ConnectionError),
        ):
            msg = (
                "Unexpected error communicating with Absurdia.  "
                "If this problem persists, let us know at "
                "support@absurdia.eu."
            )
            err = "%s: %s" % (type(e).__name__, str(e))
            should_retry = True
        # Catch remaining request exceptions
        elif isinstance(e, requests.exceptions.RequestException):
            msg = (
                "Unexpected error communicating with Absurdia.  "
                "If this problem persists, let us know at "
                "support@absurdia.eu."
            )
            err = "%s: %s" % (type(e).__name__, str(e))
            should_retry = False
        else:
            msg = (
                "Unexpected error communicating with Absurdia. "
                "It looks like there's probably a configuration "
                "issue locally.  If this problem persists, let us "
                "know at support@absurdia.eu."
            )
            err = "A %s was raised" % (type(e).__name__,)
            if str(e):
                err += " with error message %s" % (str(e),)
            else:
                err += " with no error message"
            should_retry = False

        msg = textwrap.fill(msg) + "\n\n(Network error: %s)" % (err,)
        raise error.APIConnectionError(msg, should_retry=should_retry)

    def close(self):
        if getattr(self._thread_local, "session", None) is not None:
            self._thread_local.session.close()

 