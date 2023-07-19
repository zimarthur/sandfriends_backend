from datetime import datetime
from ..asaas_base_api import requestPost

def refundPayment(paymentId, description):
    response = requestPost(
        f"payments/{paymentId}/refund", 
        {
            "description": description
        }
    )
    return response