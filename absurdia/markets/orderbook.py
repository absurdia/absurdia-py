from absurdia import util
from absurdia import api_requestor
from absurdia.markets.abstract import MarketResource

class Orderbook(MarketResource):
    OBJECT_NAME = "orderbook"
    RETRIEVED_AT = 0
    LATEST_ORDERBOOK = None
    def __init__(self, symbol: str):
        super().__init__()
        self.symbol = symbol

    def current(
        self, absurdia_version=None, absurdia_account=None, force_refresh=False, **params
    ):
        if Orderbook.RETRIEVED_AT < (util.current_timestamp('ms') - 100) \
        or force_refresh:
            Orderbook.RETRIEVED_AT = util.current_timestamp('s')
            requestor = api_requestor.APIRequestor(
                api_version=absurdia_version, account=absurdia_account
            )
            url = super().class_url()
            response = requestor.request("get", url, {"symbol" : self.symbol})
            response = util.convert_to_absurdia_object(
                response, None, absurdia_version, absurdia_account
            )
            Orderbook.LATEST_ORDERBOOK = response
        return Orderbook.LATEST_ORDERBOOK
    
    @classmethod
    def get(cls, symbol=None, **params):
        if cls.LATEST_ORDERBOOK is None:
            cls.current(symbol=symbol, **params)

def get_latest_orderbook(symbol: str):
    return Orderbook(symbol=symbol).current()