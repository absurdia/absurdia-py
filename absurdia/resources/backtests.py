from logging import warning
from absurdia.absurdia_object import AbsurdiaObject, AbsurdiaObjectsList
from absurdia.api_response import APIResponse
from absurdia.resources import ResourceRequestor
from absurdia.util import get_host_info

class BacktestsRequestor(ResourceRequestor): 
    @property
    def base_path(self):
        return "/v1/backtests"
    
    def from_response(self, response: APIResponse, is_list: bool = False):
        if response.status_code >= 300:
            raise ValueError(
                "Invalid response. The response status code is %s" 
                % (response.status_code,)
            )
        if is_list:
            return BacktestsList(response)
        else:
            return Backtest(response)
    
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
            "POST", path, data=data, timeout=30000
        )
        return self.from_response(response)
    
class BacktestsList(AbsurdiaObjectsList):
    def __init__(self, response: APIResponse):
        super().__init__(objects=response.json["data"], response=response)
        
class Backtest(AbsurdiaObject):
    def __init__(self, response: APIResponse):
        super().__init__(response=response)