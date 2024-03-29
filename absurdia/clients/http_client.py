import logging
from requests import Request, Session, hooks
from requests.adapters import HTTPAdapter
from urllib.parse import urlencode

from absurdia.api_response import APIResponse
from absurdia.util import now_ms

_logger = logging.getLogger('absurdia.http_client')


class HttpClient():
    """
    General purpose HTTP Client for interacting with the Absurdia API
    """

    def __init__(self, 
                 pool_connections=True, 
                 request_hooks=None, 
                 timeout=None, 
                 logger=_logger, 
                 log_level='WARNING', 
                 proxy=None,
                 max_retries=None):
        """
        Constructor for the HttpClient
        :param bool pool_connections
        :param request_hooks
        :param int timeout: Timeout for the requests, in milliseconds.
                            Timeout should never be zero (0) or less.
        :param logger
        :param dict proxy: Http proxy for the requests session
        :param int max_retries: Maximum number of retries each request should attempt
        """
        self.session = Session() if pool_connections else None
        if self.session and max_retries is not None:
            self.session.mount('https://', HTTPAdapter(max_retries=max_retries))
        self.last_request = None
        self.last_response = None
        self.logger = logger
        self.logger.setLevel(log_level)
        self.request_hooks = request_hooks or hooks.default_hooks()

        if timeout is not None and timeout <= 0:
            raise ValueError("Timeout should never be zero (0) or less.")
        self.timeout = timeout
        self.proxy = proxy if proxy else {}
        
        self.last_request_duration_ms = 0

    def request(self, method, url, params=None, data=None, headers=None, timeout=None,
                allow_redirects=False):
        """
        Make an HTTP Request with parameters provided.
        :param str method: The HTTP method to use
        :param str url: The URL to request
        :param dict params: Query parameters to append to the URL
        :param dict data: Dict to go as JSON in the body of the HTTP request
        :param dict headers: HTTP Headers to send with the request
        :param tuple auth: Basic Auth arguments
        :param float timeout: Socket/Read timeout for the request
        :param boolean allow_redirects: Whether or not to allow redirects
        See the requests documentation for explanation of all these parameters
        :return: An http response
        :rtype: A :class:`APIResponse <absurdia.api_response.APIResponse>` object
        """
        if timeout is not None and timeout <= 0:
            raise ValueError(timeout)

        kwargs = {
            'method': method.upper(),
            'url': url,
            'params': params,
            'json': data,
            'headers': headers,
            'hooks': self.request_hooks
        }

        self._log_request(kwargs)

        self.last_response = None
        session = self.session or Session()
        request = Request(**kwargs)
        self.last_request = request

        prepped_request = session.prepare_request(request)

        settings = session.merge_environment_settings(
            prepped_request.url, self.proxy, None, None, None)

        settings['allow_redirects'] = allow_redirects
        settings['timeout'] = timeout if timeout is not None else self.timeout

        request_start_time = now_ms()
        response = session.send(prepped_request, **settings)
        self.last_request_duration_ms = request_start_time - now_ms()
        
        self._log_response(response)

        self.last_response = APIResponse(
            int(response.status_code), response.text, response.headers)

        return self.last_response

    def _log_request(self, kwargs):
        self.logger.info('-- BEGIN Absurdia API Request --')

        if kwargs['params']:
            self.logger.info('{} Request: {}?{}'.format(
                kwargs['method'], kwargs['url'], urlencode(kwargs['params']))
            )
            self.logger.info('Query Params: {}'.format(kwargs['params']))
        else:
            self.logger.info('{} Request: {}'.format(kwargs['method'], kwargs['url']))

        if kwargs['headers']:
            self.logger.info('Headers:')
            for key, value in kwargs['headers'].items():
                # Do not log authorization headers
                if 'authorization' not in key.lower():
                    self.logger.info('{} : {}'.format(key, value))
        self.logger.debug("Request Body: {}".format(kwargs['json']))
        self.logger.info('-- END Absurdia API Request --')

    def _log_response(self, response):
        self.logger.info('Response Status Code: {}'.format(response.status_code))
        self.logger.info('Response Headers: {}'.format(response.headers))
        self.logger.debug('Reponse Body: {}'.format(response.text))