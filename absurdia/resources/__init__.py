from absurdia.clients import Client

class ResourceRequestor:
    
    def __init__(self, client: Client):
        self._client = client
    
    def from_response(self, response, is_list=False):
        raise NotImplementedError("Method not implemented.")
    
    def retrieve(self, id: str, params: dict = {}, additional_headers: dict = {}):
        path = "%s/%s" % (self.base_path, id)
        response = self._client.request(
            "GET", path, params=params, additional_headers=additional_headers
        )
        return self.from_response(response)
    
    def list(self, params: dict = { "limit": 100 }, additional_headers: dict = {}):
        if params.get("limit"):
            if params["limit"] > 1000:
                raise ValueError("Limit is too large. Its maximum value is 1000.")

        response = self._client.request(
            "GET", self.base_path, params=params, additional_headers=additional_headers
        )
        return self.from_response(response, is_list=True)

    def create(self, data: dict = {}, additional_headers: dict = {}, timeout=5000):
        return self._client.request(
            "POST", self.base_path, data=data, 
            additional_headers=additional_headers, timeout=timeout
        )
    
    def update(self, 
               id:str, 
               data: dict = {}, 
               additional_headers: dict = {}, 
               timeout=5000):
        path = "%s/%s" % (self.base_path, id)
        return self._client.request(
            "PATCH", path, data=data, 
            additional_headers=additional_headers, timeout=timeout
        )
        
    def delete(self, id: str):
        path = "%s/%s" % (self.base_path, id)
        return self._client.request("DELETE", path)