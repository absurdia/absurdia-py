from absurdia.markets.abstract import MarketResource

class Trade(MarketResource):
    OBJECT_NAME = "trade"
    LATEST_TRADES = {}
    
    def __init__(self, symbol: str):
        super().__init__(symbol)
        Trade.LATEST_TRADES[symbol] = self

    def get(self):
        return self.refresh()

def get_latest_trades(symbol: str):
    return Trade(symbol=symbol)