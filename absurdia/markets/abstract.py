from absurdia.absurdia_object import AbsurdiaObject
from absurdia import api_requestor, util
from absurdia.absurdia_response import AbsurdiaResponse

class MarketResource():
    def __init__(self, requestor=None, cache=None, **params):
        if requestor:
            self.__requestor = requestor
        else:
            self.__requestor = api_requestor.APIRequestor(**params)
        self.__retrieved_at = 0
        self.value = None
        self.id = None
        self.symbol = None
        if cache is None:
            self.__cache = 0
        else:
            self.__cache = cache

    @classmethod
    def class_url(cls):
        if cls == MarketResource:
            raise NotImplementedError(
                "MarketResource is an abstract class.  You should perform "
                "actions on its subclasses (e.g. agent, fund)"
            )
        # Namespaces are separated in object names with periods (.) and in URLs
        # with forward slashes (/), so replace the former with the latter.
        base = cls.OBJECT_NAME.replace(".", "/")
        return "/v1/%ss" % (base,)
    
    def get_(self, symbol=None, force=False, **params):
        if self.__retrieved_at < (util.current_timestamp('ms') - self.__cache) \
        or force:
            url = self.class_url()
            if symbol:
                symbol = {"symbol": symbol}
            self.value = self.__requestor.request("get", url, params=symbol, headers=None, body=params)
        return self.value.data
