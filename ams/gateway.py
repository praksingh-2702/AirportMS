"""A SIMULATED payment gateway. It never contacts anything and never moves money; it decides approve/decline
from the details given so the payment flow (and its error paths) can be demonstrated and tested.

Test values:  card 4111 1111 1111 1111 -> approved      card 4000 0000 0000 0002 -> declined by the bank
              card 4000 0000 0000 9995 -> insufficient funds      UPI id containing "fail" -> rejected
              bank "Demo Bank (offline)" -> bank server unavailable      anything else valid -> approved
"""
from dataclasses import dataclass

from .payments_core import gateway_reference

DECLINED_CARDS = {
    "4000000000000002": "Card declined by the issuing bank.",
    "4000000000009995": "Insufficient funds on this card.",
}


@dataclass(frozen=True)
class GatewayResult:
    approved: bool
    reference: str
    message: str


def authorize(method: str, details: dict, amount: int) -> GatewayResult:
    ref = gateway_reference()
    if method == "CARD":
        message = DECLINED_CARDS.get(str(details.get("number", "")))
        if message:
            return GatewayResult(False, ref, message)
    elif method == "UPI":
        if "fail" in str(details.get("upi_id", "")).lower():
            return GatewayResult(False, ref, "The UPI collect request was rejected. Check your UPI app and try again.")
    elif method == "NETBANKING":
        if "offline" in str(details.get("bank", "")).lower():
            return GatewayResult(False, ref, "The bank's server is not responding. Try again or use another method.")
    return GatewayResult(True, ref, "Approved")
