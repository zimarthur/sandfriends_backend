from datetime import datetime
from ..asaas_base_api import requestPost

from ...extensions import db
from ...utils import getFirstDayOfMonth, getLastDayOfMonth
from ...Models.store_model import Store
from ...Models.store_court_model import StoreCourt
from ...Models.match_model import Match
from ...encryption import encrypt_aes, decrypt_aes
import os

def getSplitPercentage(store, value, billingType):
    #Número de quadras do estabelecimento - não usando no momento
    numberOfCourts = db.session.query(StoreCourt)\
        .filter(StoreCourt.IdStore == store.IdStore).count()
    
    #Número de partidas neste mês no estabelecimento
        #Partidas nesta quadra
        #Partidas não canceladas        
        #Partidas no mês
    currentMonthMatches = db.session.query(Match)\
        .filter(Match.IdStoreCourt.in_([court.IdStoreCourt for court in store.Courts]))\
        .filter(Match.Canceled == False)\
        .filter((Match.CreationDate >= getFirstDayOfMonth(datetime.now())) & (Match.CreationDate >= getLastDayOfMonth(datetime.now())) ).all()        
    
    #Quantas horas de partida no mês
    currentMonthMatchesHours=0
    for match in currentMonthMatches:
        if match.isPaymentExpired == False:
            currentMonthMatchesHours += match.MatchDuration()

    #Taxas do Asaas (Flat em R$ e Perc em %)
    feeAsaas = {
        "PIX": {
            "flat": 1.99,
            "percentage": 0
        },
        "CREDIT_CARD": {
            "flat": 0.49,
            "percentage": 2.99
        }
    }

    #Taxa do Sandfriends (em %)
    if (currentMonthMatchesHours) < store.FeeThreshold:
        feeSandfriends = store.FeeSandfriendsHigh
    else:
        feeSandfriends = store.FeeSandfriendsLow
        
    ####Ajuste do split
    #Asaas cobra as taxas deles sobre o valor total
    valorPosAsaas = value * (1 - feeAsaas[billingType]["percentage"]/100) - feeAsaas[billingType]["flat"]
    #Valor que cobraremos do valor total (Contém a taxa do Sandfriends + taxa do Asaas)
    valorPosSandfriends = value * (1 - feeSandfriends/100)
    #Quanto o Sandfriends receberia pela partida
    parcelaSandfriends = valorPosAsaas - valorPosSandfriends
    #Percentual de split para considerar no Asaas
    split = parcelaSandfriends / valorPosAsaas

    #Precisa retornar um valor de 0 a 100 - o valor é o quanto vai para a walled da loja
    return round((1 - split) * 100,2)
    #return parcelaSandfriends

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
                "percentualValue": getSplitPercentage(store, value, "PIX"),
                }
            ]
        }
    )
    return response

def createPaymentCreditCard(user, value, creditCard, store, cvv):
    response = requestPost(
        f"payments", 
        {
            "customer": user.AsaasId,
            "billingType": "CREDIT_CARD",
            "value": value,
            "dueDate": datetime.now().strftime("%Y-%m-%d"),
            "creditCard": { 
                "holderName": creditCard.OwnerName,
                "number": decrypt_aes(creditCard.CardNumber, os.environ['ENCRYPTION_KEY']),
                "expiryMonth" :creditCard.ExpirationDate.strftime("%m"),
                "expiryYear": creditCard.ExpirationDate.strftime("%Y"),
                "ccv": cvv,
            },
            "creditCardHolderInfo": {
                "name": creditCard.OwnerName,
                "cpfCnpj": creditCard.OwnerCpf,
                "email": user.Email,
                "postalCode": creditCard.Cep,
                "addressNumber": creditCard.AddressNumber,
                "phone": creditCard.PhoneNumber
            },
            "split": [
                {
                "walletId":  store.AsaasWalletId,
                "percentualValue": getSplitPercentage(store, value, "CREDIT_CARD"),
                }
            ]
        }
    )
    return response

#                "percentualValue": getSplitPercentage(store, value, "CREDIT_CARD"),

# def createPaymentCreditCard(user, value, creditCard, store):
#     response = requestPost(
#         f"payments", 
#         {
#             "customer": user.AsaasId,
#             "billingType": "CREDIT_CARD",
#             "value": value,
#             "dueDate": datetime.now().strftime("%Y-%m-%d"),
#             "creditCardToken": creditCard.CreditCardToken,
#             "split": [
#                 {
#                 "walletId":  store.AsaasWalletId,
#                 "percentualValue": getSplitPercentage(store, value, billingType),
#                 }
#             ]
#         }
#     )
#     return response

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



   