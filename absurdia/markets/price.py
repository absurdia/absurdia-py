from absurdia.markets.abstract import MarketResource

class Price(MarketResource):
    OBJECT_NAME = "price"
    LATEST_PRICES = {}
    
    def __init__(self, symbol: str):
        super().__init__(symbol)
        Price.LATEST_PRICES[symbol] = self

    def get(self):
        return self.refresh()

def get_latest_price(symbol: str):
    #price = Price.LATEST_PRICES.get(symbol)
    #if price:
    #    return price.refresh()
    #else:
    #    return Price(symbol).refresh()
    return Price.retrieve(symbol=symbol)