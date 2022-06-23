from absurdia.markets.abstract import MarketResource

class Trades(MarketResource):
    OBJECT_NAME = "trade"
    LATEST_TRADES = {}
    
    def __init__(self, symbol: str):
        super().__init__()
        Trades.LATEST_TRADES[symbol] = self
        self.symbol = symbol

    def get(self):
        return self.get_(symbol=self.symbol)

def get_latest_trades(symbol: str):
    return Trades(symbol=symbol).get()