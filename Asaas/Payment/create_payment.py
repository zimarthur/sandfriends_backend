from datetime import datetime
from ..asaas_base_api import requestPost

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

def createPaymentCreditCard(user, value, creditCard):
    response = requestPost(
        f"payments", 
        {
            "customer": user.AsaasId,
            "billingType": "CREDIT_CARD",
            "value": value,
            "dueDate": datetime.now().strftime("%Y-%m-%d"),
            "creditCardToken": creditCard.CreditCardToken,
        }
    )
    return response

def createPaymentPreAuthorization(user, holderName, holderCpf, cardNumber, expirationMonth, expirationYear, cvv, cep, addressNumber):
    response = requestPost(
        "payments", 
        {
            "customer": user.AsaasId,
            "billingType": "CREDIT_CARD",
            "value": 5,
            "dueDate": datetime.now().strftime("%Y-%m-%d"),
            "authorizeOnly": True,
            "creditCard": { 
                "holderName": holderName,
                "number": cardNumber,
                "expiryMonth" :expirationMonth,
                "expiryYear": expirationYear,
                "ccv": cvv,
            },
            "creditCardHolderInfo": {
                "name": holderName,
                "cpfCnpj": holderCpf,
                "email": user.Email,
                "postalCode": cep,
                "addressNumber": addressNumber,
                "phone": user.PhoneNumber
            }
        }
    )
    return response



   