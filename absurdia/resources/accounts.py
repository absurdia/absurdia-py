from absurdia.absurdia_object import AbsurdiaObject, AbsurdiaObjectsList
from absurdia.api_response import APIResponse
from absurdia.resources import ResourceRequestor

class AccountsList(AbsurdiaObjectsList):
    def __init__(self, response: APIResponse):
        super().__init__(objects=response.json["data"], response=response)
        
class Account(AbsurdiaObject):
    def __init__(self, response: APIResponse):
        super().__init__(response=response)

class AccountsRequestor(ResourceRequestor):
    @property
    def base_path(self):
        return "/v1/accounts"
    
    def from_response(self, response: APIResponse, is_list: bool = False):
        if response.status_code >= 300:
            raise ValueError(
                "Invalid response. The response status code is %s" 
                % (response.status_code,)
            )
        if is_list:
            return AccountsList(response=response)
        else:
            return Account(response)
    
    def current(self) -> Account:
        path = "%s?current=true" % (self.base_path,)
        response = self._client.request("GET", path)
        return self.from_response(response)