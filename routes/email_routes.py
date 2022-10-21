# from flask import Blueprint, jsonify, abort, request
# from ..extensions import mail
# from ..settings import mailjet



# bp_emails = Blueprint('bp_emails', __name__)

# @bp_emails.route("/email", methods=["POST"])
# def index():
#     data = {
#     'Messages': [
#         {
#         "From": {
#             "Email": "contato@sandfriends.com.br",
#             "Name": "Arthur"
#         },
#         "To": [
#             {
#             "Email": "contato@sandfriends.com.br",
#             "Name": "Arthur"
#             }
#         ],
#         "Subject": "Email automatico SandFriends",
#         "TextPart": "Meu Primeiro email",
#         "HTMLPart": "<h3>Recebendo o primeiro email automatico</h3><br />Vamo dale",
#         #"HTMLPart": "<h3>Dear passenger 1, welcome to <a href='https://www.mailjet.com/'>Mailjet</a>!</h3><br />May the delivery force be with you!",
#         "CustomID": "AppGettingStartedTest"
#         }
#     ]
#     }
#     result = mailjet.send.create(data=data)
#     print (result.status_code)
#     print (result.json())
#     return "Message sent!"