from ..Asaas.asaas_base_api import requestPost

def generateQrCode(paymentId):
    response = requestPost(
        f"payments/{paymentId}/pixQrCode", 
        {}
    )
    return response


   