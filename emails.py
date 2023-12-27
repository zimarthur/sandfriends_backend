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
STORE_AWAITING_APPROVAL = 5237400
STORE_MATCH_CONFIRMED = 5496096

USER_MATCH_CONFIRMED = 4954742
USER_RECURRENT_MATCH_CONFIRMED = 4978838
USER_RECEIVE_COUPON = 5428798

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

#Avisar sobre quadra nova - somente para nós 3
def emailStoreAwaitingApproval(store, employee, city):
    variables = {
        "store": store.Name,
        "city": city.City,
        "email": employee.Email,
        "fullname": f"{employee.FirstName} {employee.LastName}",
        "phone1": f"({store.PhoneNumber1[0:2]}) {store.PhoneNumber1[2:7]}-{store.PhoneNumber1[7:12]}",
        "phone2": f"({store.PhoneNumber2[0:2]}) {store.PhoneNumber2[2:7]}-{store.PhoneNumber2[7:12]}",
    }
    sendEmail("Admin","", STORE_AWAITING_APPROVAL, variables)

#Cupom de desconto para o usuário
def emailUserReceiveCoupon(email, coupon):
    variables = {
        "couponcode": coupon.Code,
        "store": coupon.StoreValid.Name,
        "value": f"R$ {coupon.Value}",
    }
    sendEmail(email,"", USER_RECEIVE_COUPON, variables)

#Partida nova - e-mail para a quadra
def emailStoreMatchConfirmed(match):
    #Ajuste para deixar mais humano os textos de pagamento
    payment_type = match.AsaasBillingType
    if payment_type == "PIX":
        payment_type = "Pix"
    elif payment_type == "CREDIT_CARD":
        payment_type = "Cartão de crédito"
    elif payment_type == "PAY_IN_STORE":
        payment_type = "Pagar no local"
    else:
        payment_type = "Pagamento não localizado, entre em contato com a equipe Sandfriends para mais informações"
    
    #Telefone, caso ele não tenha
    phone = match.matchCreator().User.PhoneNumber
    if phone is None or phone == "":
        phone = "Usuário não informou"
    else:
        phone = f"({match.matchCreator().User.PhoneNumber[0:2]}) {match.matchCreator().User.PhoneNumber[2:7]}-{match.matchCreator().User.PhoneNumber[7:12]}"

    variables = {
        "date": match.Date.strftime("%d/%m/%Y"),
        "time": f"{match.TimeBegin.HourString} - {match.TimeEnd.HourString}",
        "sport": match.Sport.Description,
        "store_court": match.StoreCourt.Description,
        "name": match.matchCreator().User.FirstName + " " + match.matchCreator().User.LastName,
        "phone": phone,
        "price": f"R$ {int(match.Cost)},00",
        "payment_type": payment_type,
    }

    #Envia um e-mail para cada employee
    employees = [employee for employee in match.StoreCourt.Store.Employees]
    for employee in employees:
        sendEmail(employee.Email,"", STORE_MATCH_CONFIRMED, variables)

def sendEmail(email, name, templateId, variables):
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
    # if os.environ['AMBIENTE'] == "prod" or os.environ['AMBIENTE'] == "demo":
    if os.environ['AMBIENTE'] == "prod":
        emailToSend = email_account
    else:
        emailToSend = emails_admin

    #Caso deva ir para os admin de qualquer forma
    if email == "Admin":
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