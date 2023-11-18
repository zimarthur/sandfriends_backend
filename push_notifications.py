import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging
import os


def sendMatchPaymentAcceptedNotification(user, match, employees):
    messageUser = messaging.Message(
        token= user.NotificationsToken,
        notification=messaging.Notification(
            title='Pagamento aprovado!',
            body='Tudo certo para sua partida do dia '+match.Date.strftime('%d/%m') + ' às '+match.TimeBegin.HourString+'. Toque para ver a partida.',
        ),
        data={
            "type": "match",
            "matchUrl": match.MatchUrl,
        }
    )
    responseUser = messaging.send(messageUser)
    print('Successfully sent message to user:', responseUser)
    print("on employees, len is  "+str(len(employees)))
    messageEmployees = messaging.MulticastMessage(
        notification=messaging.Notification(
            title='Pagamento aprovado!',
            body='Tudo certo para sua partida do dia '+match.Date.strftime('%d/%m') + ' às '+match.TimeBegin.HourString+'. Toque para ver a partida.',
        ),
        data={
            "type": "match",
            "matchUrl": match.MatchUrl,
        },
        tokens= availableEmployeesList(employees),
    )
    responseEmployees = messaging.send_multicast(messageEmployees)
    print('Successfully sent message to employees:', responseEmployees)

def sendMatchInvitationNotification(userCreator, userInvite, match ):
    if userCreator.AllowNotifications != True:
        return

    message = messaging.Message(
        token= userCreator.NotificationsToken,
        notification=messaging.Notification(
            title= userInvite.fullName()+' quer entrar na sua partida!',
            body='Partida do dia '+match.Date.strftime('%d/%m') + ' às '+match.TimeBegin.HourString+'. Toque para ver a solicitação.',
        ),
        data={
            "type": "match",
            "matchUrl": match.MatchUrl,
        }
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)
    

def sendMatchInvitationAcceptedNotification(userCreator, userInvite, match ):
    if userInvite.AllowNotifications != True:
        return

    message = messaging.Message(
        token= userInvite.NotificationsToken,
        notification=messaging.Notification(
            title= userCreator.fullName()+' aceitou seu convite!',
            body='Partida do dia '+match.Date.strftime('%d/%m') + ' às '+match.TimeBegin.HourString+'. Toque para ver a partida.',
        ),
        data={
            "type": "match",
            "matchUrl": match.MatchUrl,
        }
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)

def sendMatchInvitationRefusedNotification(userCreator, userInvite, match ):
    if userInvite.AllowNotifications != True:
        return

    message = messaging.Message(
        token= userInvite.NotificationsToken,
        notification=messaging.Notification(
            title= userCreator.fullName()+' recusou seu convite :(',
            body='Partida do dia '+match.Date.strftime('%d/%m') + ' às '+match.TimeBegin.HourString+'.',
        ),
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)

def sendMemberLeftMatchNotification(userCreator, userLeft, match ):
    if userCreator.AllowNotifications != True:
        return

    message = messaging.Message(
        token= userCreator.NotificationsToken,
        notification=messaging.Notification(
            title= userLeft.fullName()+' saiu da sua partida :(',
            body='Partida do dia '+match.Date.strftime('%d/%m') + ' às '+match.TimeBegin.HourString+'. Toque para ver a partida.',
        ),
        data={
            "type": "match",
            "matchUrl": match.MatchUrl,
        }
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)

def sendMatchCanceledFromStoreNotification(store, user, match ):
    if user.AllowNotifications != True:
        return

    message = messaging.Message(
        token= user.NotificationsToken,
        notification=messaging.Notification(
            title= store.Name+' cancelou sua partida :(',
            body='Partida do dia '+match.Date.strftime('%d/%m') + ' às '+match.TimeBegin.HourString+'.',
        ),
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)

def sendMatchCanceledFromCreatorNotification(userCreator, user, match ):
    if user.AllowNotifications != True:
        return

    message = messaging.Message(
        token= user.NotificationsToken,
        notification=messaging.Notification(
            title= user.fullName()+' cancelou a partida :(',
            body='Partida do dia '+match.Date.strftime('%d/%m') + ' às '+match.TimeBegin.HourString+'. Toque para ver a partida.',
        ),
        data={
            "type": "match",
            "matchUrl": match.MatchUrl,
        }
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)

def availableEmployeesList(employees):
    employeesNotificationToken = []
    for employee in employees:
        if employee.AllowNotifications == True:
            employeesNotificationToken.append(employee.NotificationsToken)
            print("employee "+employee.NotificationsToken)
    return employeesNotificationToken