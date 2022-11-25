from absurdia.absurdia_object import AbsurdiaObject
from absurdia.api_error import APIError
from absurdia.api_response import APIResponse
from absurdia.resources import ResourceRequestor


class User(AbsurdiaObject):
    def __init__(self, response: APIResponse):
        super().__init__(response=response)

class UsersRequestor(ResourceRequestor):
    
    @property
    def base_path(self):
        return "/v1/users"
    
    def from_response(self, response: APIResponse, is_list: bool = False):
        if not response.ok:
            raise APIError(response.text, response.status_code, response.headers)
        
        if is_list:
            return NotImplementedError("Users lists are not supported yet.")
        else:
            return User(response)
        
    def list(self, params: dict = { "limit": 100 }, additional_headers: dict = {}):
        return NotImplementedError("This method is not allowed for the resource Users.")
    
    def current(self) -> User:
        path = "%s" % (self.base_path,)
        response = self._client.request("GET", path)
        return self.from_response(response)
