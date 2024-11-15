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
    sendEmployeesNewMatchNotification(match, employees)

def sendEmployeesNewMatchNotification(match, employees):
    messageEmployees = messaging.MulticastMessage(
        notification=messaging.Notification(
            title='Nova partida agendada!',
            body= 'Dia: '+match.Date.strftime('%d/%m')+ ' - ' +match.TimeBegin.HourString+' às '+match.TimeEnd.HourString+ ' (R$'+str(match.Cost).replace('.', ',')+')\nPor: '+match.matchCreator().User.fullName(),
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

def sendMatchCanceledFromCreatorNotification(match ):
    userNotificationTokensList =[]
    for matchMember in match.Members:
        if matchMember.IsMatchCreator == True:
            matchCreator = matchMember.User.fullName()
        elif matchMember.isInMatch() and matchMember.User.AllowNotifications:
            print("aaa")
            userNotificationTokensList.append(matchMember.User.NotificationsToken)
    
    messageUsers = messaging.MulticastMessage(
        notification=messaging.Notification(
            title= matchCreator+' cancelou a partida :(',
            body='Partida do dia '+match.Date.strftime('%d/%m') + ' às '+match.TimeBegin.HourString+'.',
        ),
        data={
            "type": "match",
            "matchUrl": match.MatchUrl,
        },
        tokens= userNotificationTokensList + availableEmployeesList(match.StoreCourt.Store.Employees),
    )
    responseUsers = messaging.send_multicast(messageUsers)
    print('Successfully sent message to employees:', responseUsers)


def sendStudentConfirmedClassNotification(teacher, user, match ):
    if teacher.AllowNotifications != True:
        return

    message = messaging.Message(
        token= teacher.NotificationsToken,
        notification=messaging.Notification(
            title= user.fullName()+' confirmou presença na sua aula!',
            body= 'Aula dia '+ match.Date.strftime('%d/%m') + ' às '+match.TimeBegin.HourString+'.',
        ),
        data={
            "type": "match",
            "matchUrl": match.MatchUrl,
        },
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)

def sendStudentUnconfirmedClassNotification(teacher, user, match ):
    if teacher.AllowNotifications != True:
        return

    message = messaging.Message(
        token= teacher.NotificationsToken,
        notification=messaging.Notification(
            title= user.fullName()+' saiu da sua aula :(',
            body= 'Aula dia '+ match.Date.strftime('%d/%m') + ' às '+match.TimeBegin.HourString+'.',
        ),
        data={
            "type": "match",
            "matchUrl": match.MatchUrl,
        },
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)

def sendClassCanceledByTeacher(match):
    userNotificationTokensList =[]
    for matchMember in match.Members:
        print(matchMember.User.FirstName)
        print(str(matchMember.IsMatchCreator))
        print(str(matchMember.isInMatch()))
        print(str(matchMember.User.AllowNotifications))
        if matchMember.IsMatchCreator == True:
            matchCreator = matchMember.User.fullName()
        elif matchMember.isInMatch() and matchMember.User.AllowNotifications:
            userNotificationTokensList.append(matchMember.User.NotificationsToken)
    
        print("no send NOTIG")
    for a in userNotificationTokensList:
        print(a)
    messageUsers = messaging.MulticastMessage(
        notification=messaging.Notification(
            title= matchCreator+' cancelou a aula :(',
            body='Aula do dia '+match.Date.strftime('%d/%m') + ' às '+match.TimeBegin.HourString+'.',
        ),
        data={
            "type": "match",
            "matchUrl": match.MatchUrl,
        },
        tokens= userNotificationTokensList,
    )
    responseUsers = messaging.send_multicast(messageUsers)
    print('Successfully sent message to employees:', responseUsers)

def sendStudentRequestJoinTeamNotification(team, user ):
    if team.User.AllowNotifications != True:
        return

    message = messaging.Message(
        token= team.User.NotificationsToken,
        notification=messaging.Notification(
            title= user.fullName()+' quer entrar na sua turma',
            body= 'Turma: '+team.Name,
        ),
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)

def sendTeacherResponseTeamInvitationNotification(team, user, accepted ):
    if user.AllowNotifications != True:
        return

    if accepted:
        responseText = "aceito"
    else:
        responseText = "recusado"
    
    message = messaging.Message(
        token= user.NotificationsToken,
        notification=messaging.Notification(
            title= 'Convite '+responseText, 
            body= 'Seu convite para a turma '+team.Name+' foi '+ responseText,
        ),
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)

def sendSchoolInvitationToTeacherNotification(school, user):
    if user.AllowNotifications != True:
        return

    message = messaging.Message(
        token= user.NotificationsToken,
        notification=messaging.Notification(
            title= 'Você recebeu um convite da escola ' +school.Name, 
            body=  'Aceite para poder dar aulas lá!',
        ),
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)
    

def availableEmployeesList(employees):
    employeesNotificationToken = []
    for employee in employees:
        if employee.AllowNotifications == True and employee.NotificationsToken is not None:
            employeesNotificationToken.append(employee.NotificationsToken)
            print("employee "+employee.NotificationsToken)
    return employeesNotificationToken