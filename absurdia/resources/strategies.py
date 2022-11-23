from absurdia.absurdia_object import AbsurdiaObject, AbsurdiaObjectsList
from absurdia.api_response import APIResponse
from absurdia.resources import ResourceRequestor

class StrategiesRequestor(ResourceRequestor): 
    @property
    def base_path(self):
        return "/v1/strategies"
    
    def from_response(self, response: APIResponse, is_list: bool = False):
        if response.status_code >= 300:
            raise ValueError(
                "Invalid response. The response status code is %s" 
                % (response.status_code,)
            )
        if is_list:
            return StrategiesList(response)
        else:
            return Strategy(response)
        
class StrategiesList(AbsurdiaObjectsList):
    def __init__(self, response: APIResponse):
        super().__init__(objects=response.json["data"], response=response)
        
class Strategy(AbsurdiaObject):
    def __init__(self, response: APIResponse):
        super().__init__(response=response)
    