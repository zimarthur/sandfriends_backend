import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging
import os

def sendMessage():
   # return str(os.path.abspath(os.path.join( os.pardir,'firebase_notifications.json')))
    #cred = credentials.Certificate('../firebase_notifications.json') #sandfriends-dev-firebase-adminsdk-bksqm-dc4e39340a
    #firebase_admin.initialize_app()

    message = messaging.Message(
        token='dImCyxH0Sq-mJoV-j5tIWR:APA91bG5KaThGBRh8fHjxiFXc3eeh0r0kJq63rbEtotCiuVtYVGuFyCUthuCZxKWN7P-cGbqC3_5MQNrIF_U6sJ_BnK0KDvqFR-E3Om_hHN2aGSZMdKiV3dNFc2mlmPVD4YYNndsSv7d',
        notification=messaging.Notification(
            title='Hello',
            body='World'
        ),
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)

def sendMatchPaymentAcceptedNotification(user, match):
    message = messaging.Message(
        token= user.NotificationsToken,
        notification=messaging.Notification(
            title='Pagamento aprovado!',
            body='Tudo certo para sua partida do dia match',
        ),
        data={
            "type": "match",
            "matchUrl": match.MatchUrl,
        }
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)
