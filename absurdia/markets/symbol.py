from absurdia import util
from absurdia.markets.abstract import MarketResource

class Symbol(MarketResource):
    OBJECT_NAME = "symbol"
    LATEST_SYMBOLS = {}

    def __init__(self, symbol: str = None, with_response=None, **params):
        super().__init__(cache=3600000, **params)
        if symbol is None:
            for symbol in self.get_():
                primary = symbol.get("symbol")
                Symbol(symbol = primary, with_response=symbol)
        else:
            symbol = symbol.upper()
            if not util.validate_symbol(symbol):
                raise ValueError("Invalid symbol")

            if symbol in Symbol.LATEST_SYMBOLS:
                self.__value = Symbol.LATEST_SYMBOLS[symbol]
                self.__primary = symbol
            else:
                if with_response is None:
                    self.__value = self.get_(symbol)[0]
                else:
                    self.__value = with_response
                self.__primary = symbol
                Symbol.LATEST_SYMBOLS[symbol] = self.__value

    def __str__(self):
        return self.__primary

    def __repr__(self):
        return "Symbol('{primary}')".format(primary=self.__primary)

    @property
    def base(self):
        return self.__value.get("base")
    
    @property
    def quote(self):
        return self.__value.get("quote")

    @property
    def market_type(self):
        return self.__value.get("market_type")
    
    @property
    def venue(self):
        return self.__value.get("exchange")

    @property
    def available_services(self):
        return self.__value.get("services")

    def refresh(self):
        super().get_(self.__primary)[0]

    @classmethod
    def get_all(cls):
        return list(cls.LATEST_SYMBOLS.values())
        
def get_symbols(**params):
    Symbol(**params)
    return Symbol.get_all()

def get_symbol(symbol: str = None, base=None, quote=None, venue=None, **params):
    if symbol is not None:
        return Symbol(symbol=symbol, **params)
    elif base is not None and quote is not None and venue is not None:
        return Symbol(base=base, quote=quote, venue=venue, **params)
