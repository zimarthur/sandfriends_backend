from .settings import mailjet


def sendEmail( message):
    data = {
    'Messages': [
        {
        "From": {
            "Email": "contato@sandfriends.com.br",
            "Name": "Arthur"
        },
        "To": [
            {
            "Email": "pedromilano902@gmail.com",
            "Name": "Pedro"
            }
        ],
        "Subject": "Email automático SandFriends",
        "TextPart": "Meu Primeiro email",
        "HTMLPart": "<h3>"+message+"</h3><br />Vamo dale",
        #"HTMLPart": "<h3>Dear passenger 1, welcome to <a href='https://www.mailjet.com/'>Mailjet</a>!</h3><br />May the delivery force be with you!",
        "CustomID": "AppGettingStartedTest"
        }
    ]
    }
    result = mailjet.send.create(data=data)
    print (result.status_code)
    print (result.json())
    return "Message sent!"