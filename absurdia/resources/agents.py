from absurdia.absurdia_object import AbsurdiaObject, AbsurdiaObjectsList
from absurdia.api_response import APIResponse
from absurdia.resources import ResourceRequestor

class AgentsList(AbsurdiaObjectsList):
    def __init__(self, response: APIResponse):
        super().__init__(objects=response.json["data"], response=response)
        
class Agent(AbsurdiaObject):
    def __init__(self, response: APIResponse):
        super().__init__(response=response)

class AgentsRequestor(ResourceRequestor):
    
    @property
    def base_path(self):
        return "/v1/agents"
    
    def from_response(self, response: APIResponse, is_list: bool = False):
        if response.status_code >= 300:
            raise ValueError(
                "Invalid response. The response status code is %s" 
                % (response.status_code,)
            )
        if is_list:
            return AgentsList(response)
        else:
            return Agent(response)
    
    def current(self) -> Agent: 
        path = "%s/%s" % (self.base_path,self._client.agent)
        response = self._client.request("GET", path)
        return self.from_response(response)   
