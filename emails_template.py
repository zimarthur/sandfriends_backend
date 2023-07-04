from mailjet_rest import Client

api_key = '8ca92dfd5c3d9c6234348a5a8b06b249'
api_secret = 'a694ad20fe5c568939a31f74e37efc61'
mailjet = Client(auth=(api_key, api_secret), version='v3.1')


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
        },
        {
        "Email": "zim.arthur97@gmail.com",
        "Name": "Arthur"
        }
    ],
    "TemplateId": 4927868,
    "TemplateLanguage": True,
     "Variables": {
            "nome": "Astor",
    }
    }
]
}
result = mailjet.send.create(data=data)
print (result.status_code)
print (result.json())
