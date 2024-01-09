from datetime import datetime
from ..asaas_base_api import requestPost

def refundPayment(paymentId, cost, description):
    response = requestPost(
        f"payments/{paymentId}/refund", 
        {
            "value": cost,
            "description": description
        }
    )
    return response