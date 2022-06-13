from absurdia.api_resources.abstract import ListableAPIResource
from absurdia import api_requestor, util
import absurdia

class Agent(ListableAPIResource):
    OBJECT_NAME = "agent"

    @classmethod
    def retrieve(cls, id=None, agent_token=None, **params):
        instance = cls(id, agent_token, **params)
        instance.refresh()
        return instance
    
    @classmethod
    def current(cls, agent_token=None, absurdia_version=None, **params):
        requestor = api_requestor.APIRequestor(agent_token, api_version=absurdia_version)
        url = cls.class_url()
        util.load_agent() # Might be necessary to find the agent id 
        body = { "id": absurdia.agent_id }
        print("Request with body: " + str(body))
        response = requestor.request("get", url, params=body, **params)
        return util.convert_to_absurdia_object(response, agent_token, absurdia_version)
