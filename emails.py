from .settings import mailjet


USER_WELCOME_CONFIRMATION = 4927868
USER_CHANGE_PASSWORD = 4927873

STORE_WELCOME_CONFIRMATION = 4927876
STORE_CHANGE_PASSWORD = 4927888
STORE_ADD_EMPLOYEE = 4927886
STORE_APPROVED = 4927883
 

def emailUserWelcomeConfirmation(email, name):
    variables = {
        "nome": "Astor",
    }
    sendEmail(email, name, USER_WELCOME_CONFIRMATION, variables)
   
def emailUserChangePassword(email, name):
    variables = {
        "nome": "Astor",
    }
    sendEmail(email, name, STORE_CHANGE_PASSWORD, variables)
   
def emailStoreWelcomeConfirmation(email, name):
    variables = {
        "nome": "Astor",
    }
    sendEmail(email, name, STORE_WELCOME_CONFIRMATION, variables)
   
def emailStoreChangePassword(email, name):
    variables = {
        "nome": "Astor",
    }
    sendEmail(email, name, STORE_CHANGE_PASSWORD, variables)
   
def emailStoreAddEmployee(email, name):
    variables = {
        "nome": "Astor",
    }
    sendEmail(email, name, STORE_ADD_EMPLOYEE, variables)

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
            "Name": "Equipe Sandfriends"
        },
        "To": [
            {
                "Email": email,
                "Name": name
            }
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