from typing import Dict, Union
from absurdia.api_resources.abstract import ListableAPIResource
from absurdia import api_requestor, util
import absurdia

class Order(ListableAPIResource):
    OBJECT_NAME = "order"
    ORDER_STATUSES = [
        "received", 
        "placed", 
        "cancelled", 
        "filled", 
        "rejected", 
        "partial_filled", 
        "partial_cancelled"
    ]
    ORDER_TYPES = [
        "market", 
        "limit", 
        "stop", 
        "stop_limit", 
        "take", 
        "take_limit"
    ]
    ORDER_SIDES = ["buy", "sell", "long", "short"]
    ORDER_TIF = ["gtc", "gtt", "fok", "ioc", "opg", "cls", "day"]
    
    @classmethod
    def create(cls,
               quantity: float,
               sent_to_venue_at: int,
               fund_id: Union[None, str]=None,
               custom_id: Union[None, str]=None,
               venue_id: Union[None, str]=None,
               venue: Union[None, str]=None,
               venue_symbol: Union[None, str]=None,
               absurdia_symbol: Union[None, str]=None,
               status: str="placed",
               type: str="market",
               market_type: str="spot",
               side: Union[None, str]=None,
               price: Union[None, float]=None,
               post_only: bool=True,
               reduce_only: bool=False,
               time_in_force: Union[None, str]=None,
               filled_at=None,
               cancelled_at=None,
               rejected_at=None,
               quantity_filled=None,
               price_filled=None,
               explanation: Union[None, str]=None,
               quote_asset: Union[None, str]=None,
               base_asset: Union[None, str]=None,
               metadata: Union[None, Dict[str, str]]=None,
               **params):
        if fund_id is None and absurdia.default_fund is None:
            raise ValueError("A fund ID is required to add an order. Either pass a fund ID or set a default fund ID with `absurdia.defaul_fund=...`.")
        elif fund_id is None:
            fund_id = absurdia.default_fund
        params["fund_id"] = fund_id
        
        if venue_symbol is None and absurdia_symbol is None:
            raise ValueError("Either a venue symbol or an Absurdia symbol is required to add an order.")
        elif venue_symbol is None:
            if util.validate_absurdia_symbol(absurdia_symbol):
                params["absurdia_symbol"] = absurdia_symbol
            else:
                raise ValueError("The Absurdia symbol is invalid.")
        else:
            if (venue in util.SUPPORTED_VENUES) or (venue in util.VENUE_MAP.keys()):
                params["venue_symbol"] = venue_symbol
                params["venue"] = venue
            else:
                raise ValueError("The venue is unsupported. Supported venues are: " + ", ".join(util.VENUE_MAP))
        
        if status.lower() in cls.ORDER_STATUSES:
            params["status"] = status.lower()
        else:
            raise ValueError("The status is unsupported. Supported statuses are: " + ", ".join(cls.ORDER_STATUSES))
        
        if market_type.lower() in ["spot", "future"]:
            params["market_type"] = market_type.lower()
        else:
            raise ValueError("The type is unsupported. Supported types are: spot, future")
        
        if type.lower() in cls.ORDER_TYPES:
            params["type"] = type.lower()
        else:
            raise ValueError("The type is unsupported. Supported types are: " + ", ".join(cls.ORDER_TYPES))
        
        if side.lower() in cls.ORDER_SIDES:
            params["side"] = side.lower()
        else:
            raise ValueError("The side is unsupported. Supported sides are: " + ", ".join(cls.ORDER_SIDES))

        if time_in_force is not None:
            if time_in_force.lower() in cls.ORDER_TIF:
                params["time_in_force"] = time_in_force.lower()
            else:
                raise ValueError("The time in force is unsupported. Supported time in forces are: " + ", ".join(cls.ORDER_TIF))
        
        if params["status"] == "filled":
            if filled_at is None:
                raise ValueError("A filled_at timestamp is required for a filled order.")
            else:
                params["filled_at"] = filled_at
                if quantity_filled is not None:
                    params["quantity_filled"] = quantity_filled
                if price_filled is not None:
                    params["price_filled"] = price_filled
        elif params["status"] == "cancelled":
            if cancelled_at is None:
                raise ValueError("A cancelled_at timestamp is required for a cancelled order.")
            else:
                params["cancelled_at"] = cancelled_at
                if explanation is not None:
                    params["explanation"] = explanation
        elif params["status"] == "rejected":
            if rejected_at is None:
                raise ValueError("A rejected_at timestamp is required for a rejected order.")
            else:
                params["rejected_at"] = rejected_at
                if explanation is not None:
                    params["explanation"] = explanation
                    
        if params["type"] in ["market", "stop", "take"]:
            if price is not None:
                raise ValueError("A price is not allowed for a `market`, `stop`, or `take` order. For filled orders, use the field `price_filled` instead.")
        elif params["type"] in ["limit", "stop_limit", "take_limit"]:
            if price is None:
                raise ValueError("A price is required for a `limit`, `stop_limit`, or `take_limit` order.")
            else:
                params["price"] = price
            
        if quote_asset:
            params["quote_asset"] = quote_asset
        if base_asset:
            params["base_asset"] = base_asset
        if custom_id:
            params["custom_id"] = custom_id
        if venue_id:
            params["venue_id"] = venue_id
        if metadata:
            params["metadata"] = metadata
        params["quantity"] = quantity
        params["sent_to_venue_at"] = sent_to_venue_at
        params["post_only"] = post_only
        params["reduce_only"] = reduce_only
        
        requestor = api_requestor.APIRequestor()
        url = cls.class_url()
        response = requestor.request("post", url, params)
        return util.convert_to_absurdia_object(response)

    @classmethod
    def retrieve(cls, id, agent_token=None, **params):
        instance = cls(id, agent_token, **params)
        instance.refresh()
        return instance

    def fill(self, 
             at: int,
             price: Union[None, float] = None, 
             quantity: Union[None, float] = None, 
             fees:  Union[None, float] = None, 
             **params
        ):
        
        if self.get("status") in ["filled", "cancelled", "rejected", "partial_cancelled"]:
            raise ValueError("This order has already been settled (status is filled, cancelled, rejected, or partial_cancelled).")
        if self.get("type") in ["market", "stop", "take"]:
            if price is None:
                raise ValueError("A filling price is required for a `market`, `stop`, or `take` order.")
            else:
                params["price_filled"] = price
        elif price is None:
            params["price_filled"] = self.get("price")
            util.logger.warn("No filling price provided. Using the order price as filling price, but this doesn't take slippage into account. Prefer adding a the real filling price.")
        else:
            params["price_filled"] = price

        if quantity:
            params["quantity_filled"] = quantity
        else:
            params["quantity_filled"] = self.get("quantity")
        if fees:
            params["fees"] = fees
        
        params["filled_at"] = at

        return self._request(
            "post",
            "/v1/orders/{order_id}/fill".format(
                order_id=util.sanitize_id(self.get("id"))
            ),
            params=params
        )
        
    def cancel(self, 
               at: int,
               explanation: Union[None, str] = None,
               **params
        ):
        if self.get("status") in ["filled", "cancelled", "rejected", "partial_cancelled"]:
            raise ValueError("This order has already been settled (status is filled, cancelled, rejected, or partial_cancelled).")
       
        params["cancelled_at"] = at
        if explanation:
            params["explanation"] = explanation

        return self._request(
            "post",
            "/v1/orders/{order_id}/cancel".format(
                order_id=util.sanitize_id(self.get("id"))
            ),
            params=params
        )
        
    def reject(self, 
               at: int,
               explanation: Union[None, str] = None,
               **params
        ):
        if self.get("status") in ["filled", "cancelled", "rejected", "partial_cancelled"]:
            raise ValueError("This order has already been settled (status is filled, cancelled, rejected, or partial_cancelled).")
        
        params["rejected_at"] = at
        if explanation:
            params["explanation"] = explanation
            
        return self._request(
            "post",
            "/v1/orders/{order_id}/reject".format(
                order_id=util.sanitize_id(self.get("id"))
            ),
            params=params
        )