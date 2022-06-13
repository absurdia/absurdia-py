from absurdia import util
from absurdia.api_resources.abstract import ListableAPIResource
from absurdia import api_requestor

class Account(ListableAPIResource):
    OBJECT_NAME = "account"

    @classmethod
    def retrieve(cls, id=None, agent_token=None, **params):
        instance = cls(id, agent_token, **params)
        instance.refresh_from(instance.request("get", instance.class_url()))
        return instance

    @classmethod
    def current(cls, agent_token=None, absurdia_version=None, **params):
        requestor = api_requestor.APIRequestor(agent_token, api_version=absurdia_version)
        url = cls.class_url()
        response = requestor.request("get", url, params)
        return util.convert_to_absurdia_object(response, agent_token, absurdia_version)
