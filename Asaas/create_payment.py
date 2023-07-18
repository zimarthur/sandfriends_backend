from datetime import datetime
from ..Asaas.asaas_base_api import requestPost

def createPaymentPix(user, value):
    response = requestPost(
        f"payments", 
        {
            "customer": user.AsaasId,
            "billingType": "PIX",
            "value": value,
            "dueDate": datetime.now().strftime("%Y-%m-%d"),
        }
    )
    return response


   