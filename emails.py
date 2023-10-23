import json
import os
from .settings import mailjet
from .utils import weekdays

USER_WELCOME_CONFIRMATION = 4954722
USER_CHANGE_PASSWORD = 4954729
USER_WELCOME_CONFIRMATION_TEST = 5076422

STORE_WELCOME_CONFIRMATION = 4927876
STORE_CHANGE_PASSWORD = 4954711
STORE_ADD_EMPLOYEE = 4954715
STORE_APPROVED = 4954730

USER_MATCH_CONFIRMED = 4954742
USER_RECURRENT_MATCH_CONFIRMED = 4978838

def emailUserMatchConfirmed(match):
    variables = {
        "link": f"https://{os.environ['URL_APP']}/redirect/?ct=mtch&bd={match.MatchUrl}",
        "store": match.StoreCourt.Store.Name,
        "date": match.Date.strftime("%d/%m/%Y"),
        "price": f"R$ {int(match.Cost)},00",
        "time": f"{match.TimeBegin.HourString} - {match.TimeEnd.HourString}",
        "sport": match.Sport.Description,
    }
    sendEmail(match.matchCreator().User.Email,"", USER_MATCH_CONFIRMED, variables)

def emailUserRecurrentMatchConfirmed(match, cost):
    variables = {
        "store": match.StoreCourt.Store.Name,
        "date": weekdays[match.Date.weekday()],
        "price": f"R$ {cost},00",
        "time": f"{match.TimeBegin.HourString} - {match.TimeEnd.HourString}",
        "sport": match.Sport.Description,
    }
    sendEmail(match.matchCreator().User.Email,"", USER_RECURRENT_MATCH_CONFIRMED, variables)

def emailUserWelcomeConfirmation(email, link):
    variables = {
        "link":link,
    }
    sendEmail(email,"", USER_WELCOME_CONFIRMATION, variables)
   
def emailUserChangePassword(email, name, link):
    variables = {
        "link":link,
    }
    sendEmail(email, name, USER_CHANGE_PASSWORD, variables)
   
def emailStoreWelcomeConfirmation(email, name, link):
    variables = {
        "link":link,
    }
    sendEmail(email, name, STORE_WELCOME_CONFIRMATION, variables)
   
def emailStoreChangePassword(email, name, link):
    variables = {
       "link":link,
    }
    sendEmail(email, name, STORE_CHANGE_PASSWORD, variables)
   
def emailStoreAddEmployee(email, link):
    variables = {
        "link":link,
    }
    sendEmail(email, email, STORE_ADD_EMPLOYEE, variables)

def emailStoreApproved(email, name):
    variables = {
        "nome": "Astor",
    }
    sendEmail(email, name, STORE_APPROVED, variables)
#Teste
def emailUserWelcomeConfirmationTest(email, link):
    variables = {
        "link":link,
    }
    sendEmail(email,"", USER_WELCOME_CONFIRMATION_TEST, variables)   
    
def sendEmail( email, name, templateId, variables):
    #Emails nossos - Irá enviar apenas no ambiente de dev
    emails_admin = [
            {
                "Email": "zim.arthur97@gmail.com",
                "Name": "Arthur"
            },
            {
                "Email": "pedromilano902@gmail.com",
                "Name": "Pedro"
            },
            {
                "Email": "pietro.berger@gmail.com",
                "Name": "Pietro"
            },
        ]
    
    #Envia para o e-mail da conta nos ambientes de demo e de prod
    email_account = [
        {
                "Email": email,
                "Name": name
        },
    ]

    #Para qual e-mail envia
    #Alterei temporariamente para não enviar diretamente para o demo, para criar os usuários de teste
    #if os.environ['AMBIENTE'] == "prod" or os.environ['AMBIENTE'] == "demo":
    if os.environ['AMBIENTE'] == "prod":
        emailToSend = email_account
    else:
        emailToSend = emails_admin

    data = {
    'Messages': [
        {
        "From": {
            "Email": "contato@sandfriends.com.br",
            "Name": "Sandfriends"
        },
        "To": emailToSend,
        "TemplateId": templateId,
        "TemplateLanguage": True,
        "Variables": variables,
        }
    ]
    }
    result = mailjet.send.create(data=data)
    print (result.status_code)
    print (result.json())
    return "Message sent!"