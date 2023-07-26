from .settings import mailjet


USER_WELCOME_CONFIRMATION = 4954722
USER_CHANGE_PASSWORD = 4954729

STORE_WELCOME_CONFIRMATION = 4927876
STORE_CHANGE_PASSWORD = 4954711
STORE_ADD_EMPLOYEE = 4954715
STORE_APPROVED = 4954730
 

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
   
    
def sendEmail( email, name, templateId, variables):
    data = {
    'Messages': [
        {
        "From": {
            "Email": "contato@sandfriends.com.br",
            "Name": "Sandfriends"
        },
        "To": [
            {
                "Email": "zim.arthur97@gmail.com",
                "Name": "Arthur"
            },
            {
                "Email": "pedromilano902@gmail.com",
                "Name": "Pedro"
            },
        ],
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