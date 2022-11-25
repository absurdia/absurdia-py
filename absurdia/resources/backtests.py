from logging import warning
from absurdia.absurdia_object import AbsurdiaObject, AbsurdiaObjectsList
from absurdia.api_error import APIError
from absurdia.api_response import APIResponse
from absurdia.resources import ResourceRequestor
from absurdia.util import get_host_info

class BacktestsRequestor(ResourceRequestor): 
    @property
    def base_path(self):
        return "/v1/backtests"
    
    def from_response(self, response: APIResponse, is_list: bool = False):
        if not response.ok:
            raise APIError(response.text, response.status_code, response.headers)
        if is_list:
            return BacktestsList(response)
        else:
            return Backtest(response)
    
    def create(
            self, 
            strategy_id: str,
            start_date: int,
            end_date: int,
            timeframe: str,
            name: str = None,
            description: str = None, 
            metadata: dict = None,
            is_public: bool = False,
            initial_balance: float = 1000.0,
            quote_currency: str = "USD",
            symbols: list = None,
            venues: list = None,
            stop_loss_ratio: float = None,
            epsilon: float = 0.01,
            markets_change: float = None,
            configs: dict = None,
            framework_name: str = None,
            framework_version: str = None
        ):
        data = { 
            "strategy_id": strategy_id,
            "start_date": start_date,
            "end_date": end_date,
            "timeframe": timeframe,
            "initial_balance": initial_balance,
            "is_public": is_public,
            "host": get_host_info()
        }
        if name: data["name"] = name
        if description: data["description"] = description
        if metadata: data["metadata"] = metadata
        if quote_currency: data["quote_currency"] = quote_currency
        if symbols: data["symbols"] = symbols
        if venues: data["venues"] = venues
        if stop_loss_ratio: data["stop_loss_ratio"] = stop_loss_ratio
        if epsilon: data["epsilon"] = epsilon
        if markets_change: data["markets_change"] = markets_change
        if configs: data["configs"] = configs
        if framework_name: 
            data["framework"] = { 
                "name": framework_name,
                "version": framework_version
            }

        response = self._client.request(
            "POST", self.base_path, data=data)
        return self.from_response(response)
    
    def import_freqtrade(
        self, 
        result: any,
        name: str = None,
        cli_command: str = None,
        host: dict = None, 
    ):
        data = {
            "adapter": "freqtrade",
            "data": result
        }
        try:
            from freqtrade import __version__
            data["framework"] = {
                "name" : "freqtrade",
                "version": __version__
            }
        except ImportError:
            warning(
                "Cannot import `freqtrade`. "
                "The version of the library will be set at 0.0.0."
            )
            data["framework"] = {
                "name": "freqtrade",
                "version": "0.0.0"
            }
        
        if host:
            data["host"] = host
        else:
            data["host"] = get_host_info()
        if name:
            data["name"] = name
        if cli_command:
            data["cli_command"] = cli_command
        
        path = "%s/import" % (self.base_path,)
        response = self._client.request(
            "POST", path, data=data, timeout=60000
        )
        return self.from_response(response)
    
class BacktestsList(AbsurdiaObjectsList):
    def __init__(self, response: APIResponse):
        super().__init__(objects=response.json["data"], response=response)
        
class Backtest(AbsurdiaObject):
    def __init__(self, response: APIResponse):
        super().__init__(response=response)
        
    def add_positions(self, positions: list):
        data = { "positions": positions }
        url = "%s/%s/positions" % (self.base_path, self.id)
        response = self._client.request("POST", url, data=data)
        if not response.ok:
            raise APIError(response.text, response.status_code, response.headers)
    
    def add_position(self, position: dict):
        return self.add_positions([position])
    
    def finish(self):
        url = "%s/%s" % (self.base_path, self.id)
        data = { "status": "finished" }
        response = self._client.request("PATCH", url, data=data)
        if not response.ok:
            raise APIError(response.text, response.status_code, response.headers)
        self.__init__(self, response)
    