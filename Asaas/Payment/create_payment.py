from datetime import datetime
from ..asaas_base_api import requestPost

from ...extensions import db
from ...utils import getFirstDayOfMonth, getLastDayOfMonth
from ...Models.store_model import Store
from ...Models.match_model import Match

def getSplitPercentage(store):
    currentMonthMatches = db.session.query(Match)\
        .filter(Match.IdStoreCourt.in_([court.IdStoreCourt for court in store.Courts]))\
        .filter(Match.Canceled == False)\
        .filter((Match.CreationDate >= getFirstDayOfMonth(datetime.now())) & (Match.CreationDate >= getLastDayOfMonth(datetime.now())) ).all()        

    currentMonthMatches = [match for match in currentMonthMatches if match.isPaymentExpired == False]

    if len(currentMonthMatches) < 50:
        return 90
    elif len(currentMonthMatches) < 100:
        return 92
    else:
        return 94

def createPaymentPix(user, value, store):
    response = requestPost(
        f"payments", 
        {
            "customer": user.AsaasId,
            "billingType": "PIX",
            "value": value,
            "dueDate": datetime.now().strftime("%Y-%m-%d"),
            "split": [
                {
                "walletId": store.AsaasWalletId,
                "percentualValue": getSplitPercentage(store),
                }
            ]
        }
    )
    return response

def createPaymentCreditCard(user, value, creditCard, store):
    response = requestPost(
        f"payments", 
        {
            "customer": user.AsaasId,
            "billingType": "CREDIT_CARD",
            "value": value,
            "dueDate": datetime.now().strftime("%Y-%m-%d"),
            "creditCardToken": creditCard.CreditCardToken,
            "split": [
                {
                "walletId":  store.AsaasWalletId,
                "percentualValue": getSplitPercentage(store),
                }
            ]
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



   