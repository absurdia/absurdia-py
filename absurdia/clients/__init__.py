import platform
import json
from absurdia.clients.http_client import HttpClient
from absurdia.util import load_agent
from absurdia.api_error import AuthenticationError
from absurdia.version import VERSION
from absurdia.agent_credentials import token

class Client():
    """ A client for accessing the Absurdia API. """
    
    def __init__(self, 
                 agent: str = None, 
                 test: bool = False, 
                 enable_telemetry: bool = True, 
                 log_level='WARNING'):

        if agent is None:
            load_agent()
            if token is None:
                raise AuthenticationError(
                    "No agent token provided. You can generate agent keys "
                    "from the Absurdia web interface. "
                    "See https://app.absurdia.markets/agents"
                )
            agent = token
        if len(agent) != 64:
            raise AuthenticationError(
                "Bad agent token provided. You can generate agent keys "
                "from the Absurdia web interface. "
                "See https://app.absurdia.markets/agents"
            )
        self.agent = agent
        
        ua = {
            "bindings_version": VERSION,
            "lang": "python",
            "publisher": "absurdia"
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

        self.base_headers = {
            "Abs-Client-Agent": json.dumps(ua),
            "User-Agent": "Absurdia/v1 PythonBindings/%s" % (VERSION,),
            "Authorization": "Bearer %s" % (self.agent,),
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip"
        }
        
        self._test = test
        self.enable_telemetry = enable_telemetry

        self.http_client = HttpClient(log_level=log_level)
        self.__last_response = None
        
        # ResourceRequestors
        self._accounts = None
        self._users = None
        self._agents = None
        self._strategies = None
        self._backtests = None
                
    @property
    def headers(self):
        if self.enable_telemetry and self.__last_response:
            if "x-request-id" in self.__last_response.headers:
                request_id = self.__last_response.headers["x-request-id"]
                telemetry = {
                    "request_metrics": {
                        "request_id": request_id,
                        "duration_ms": self.http_client.last_request_duration_ms or 0
                    }
                }
                self.base_headers["Abs-Client-Telemetry"] = json.dumps(telemetry)
        return self.base_headers
    
    @property
    def hostname(self):
        if self._test:
            return "https://test.api.absurdia.markets"
        return "https://api.absurdia.markets"
    
    def request(self, 
                method: str, 
                path: str, 
                params: dict = {}, 
                data: dict = {}, 
                additional_headers: dict = {},
                timeout: int = 5000
    ):
        """
        Makes a request to the Absurdia API using the configured http client
        Authentication information is automatically added.
        :param str method: HTTP Method
        :param str uri: Fully qualified url
        :param dict[str, str] params: Query string parameters
        :param dict[str, str] data: Request body data
        :param dict[str, str] additional_headers: HTTP Headers
        :param int timeout: Timeout in milliseconds
        :returns: Response from the API
        :rtype: absurdia.api_response.APIResponse
        """
        if not bool(params):
            params = None
        if not bool(data):
            data = None
        
        headers = self.headers.copy()
        headers.update(additional_headers)
        
        response = self.http_client.request(
            method,
            "%s%s" % (self.hostname, path),
            params=params,
            data=data,
            headers=headers,
            timeout=timeout
        )
        self.__last_response = response
        return response
        
    def __repr__(self):
        """
        Provide a friendly representation
        :returns: Machine friendly representation
        :rtype: str
        """
        return '<Absurdia Client - Agent {}>'.format(self.agent)
    
    @property
    def accounts(self):
        if self._accounts is None:
            from absurdia.resources.accounts import AccountsRequestor
            self._accounts = AccountsRequestor(self)
        return self._accounts
    
    @property
    def users(self):
        if self._users is None:
            from absurdia.resources.users import UsersRequestor
            self._users = UsersRequestor(self)
        return self._users
    
    @property
    def agents(self):
        if self._agents is None:
            from absurdia.resources.agents import AgentsRequestor
            self._agents = AgentsRequestor(self)
        return self._agents
    
    @property
    def strategies(self):
        if self._strategies is None:
            from absurdia.resources.strategies import StrategiesRequestor
            self._strategies = StrategiesRequestor(self)
        return self._strategies
    
    @property
    def backtests(self):
        if self._backtests is None:
            from absurdia.resources.backtests import BacktestsRequestor
            self._backtests = BacktestsRequestor(self)
        return self._backtests