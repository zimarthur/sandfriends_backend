from flask import Blueprint, jsonify, abort, request
from datetime import datetime
import random
from sqlalchemy import null, true, ForeignKey
from ..utils import firstSundayOnNextMonth, lastSundayOnLastMonth, getFirstDayOfLastMonth

from ..routes.reward_routes import RewardStatus
from ..responses import webResponse
from ..Models.user_model import User
from ..Models.user_credit_card_model import UserCreditCard
from ..Models.store_model import Store
from ..Models.available_hour_model import AvailableHour
from ..Models.rank_category_model import RankCategory
from ..Models.gender_category_model import GenderCategory
from ..Models.side_preference_category_model import SidePreferenceCategory
from ..Models.store_photo_model import StorePhoto
from ..Models.store_court_model import StoreCourt
from ..Models.infrastructure_category_model import InfrastructureCategory
from ..Models.sport_model import Sport
from ..Models.city_model import City
from ..Models.state_model import State
from ..Models.user_rank_model import UserRank
from ..Models.match_model import Match
from ..Models.teacher_plan_model import TeacherPlan
from ..Models.store_school_teacher_model import StoreSchoolTeacher
from ..Models.team_model import Team
from ..Models.recurrent_match_model import RecurrentMatch
from ..Models.match_member_model import MatchMember
from ..routes.match_routes import getHourString
from ..routes.match_routes import GetAvailableCitiesList
from ..Models.notification_user_model import NotificationUser
from ..Models.notification_user_category_model import NotificationUserCategory
from ..extensions import db
from ..emails import emailUserWelcomeConfirmation, emailUserChangePassword
from ..Models.http_codes import HttpCode
from ..access_token import EncodeToken, DecodeToken
import bcrypt
import json
import os
import string
import random

from ..Asaas.Customer.create_customer import createCustomer

bp_user_login = Blueprint('bp_user_login', __name__)

# Rota para cadastrar jogador
@bp_user_login.route("/AddUser", methods=["POST"])
def AddUser():
    if not request.json:
        abort(HttpCode.ABORT)

    isTeacherReq = request.json.get('IsTeacher')
    emailReq = request.json.get('Email')
    passwordReq = request.json.get('Password').encode('utf-8')
    time = datetime.now()

    user = User.query.filter_by(Email=emailReq).first()

    #Criar usuário novo
    if user:
        if user.IsTeacher is None:
            user.IsTeacher = False
        if user.IsTeacher != isTeacherReq:
            if isTeacherReq:
                return "Você já utilizou esse e-mail para uma conta jogador. Crie uma nova conta com outro e-mail.",HttpCode.WARNING
            else:
                return "Você já utilizou esse e-mail para uma conta professor. Crie uma nova conta com outro e-mail.",HttpCode.WARNING

        #O email que o usuário tentou cadastrar já foi cadastrado com o "Login com o google"
        if user.ThirdPartyLogin: 
            if user.AppleToken is not None:
                return "E-mail já cadastrado com uma conta Apple",HttpCode.ALERT
            else:
                return "E-mail já cadastrado com uma conta Google",HttpCode.ALERT

        return "Este e-mail já foi cadastrado anteriormente",HttpCode.WARNING

    userNew = User(
        Email = emailReq,
        Password = bcrypt.hashpw(passwordReq, bcrypt.gensalt()),
        AccessToken = 0, 
        RegistrationDate = time,
        ThirdPartyLogin = False,
        IsTeacher = isTeacherReq,
    )

    #A etapa abaixo acontece porque o IdUser da tabela User é incrementado automaticamente.
    #Na hora que o novo usuário é inserido, não se sabe qual o IdUser dele. Por issso tem aquele .flush(), ele faz com que esse IdUser seja "calculado"
    db.session.add(userNew)
    db.session.flush()  
    db.session.refresh(userNew)
    
    #Com o IdUser já "calculado" já da pra criar o accessToken, que é feito no arquivo access_token.py, 
    #e criar o token pra confimação do email(que é enviado por email pela função emailUserWelcomeConfirmation())
    userNew.AccessToken = EncodeToken(userNew.IdUser)
    userNew.EmailConfirmationToken = generateRandomString(16)

    if userNew.IsTeacher:
        emailUserWelcomeConfirmation(userNew.Email, "https://" + os.environ['URL_AULAS'] + "/confirme-seu-email/"+userNew.EmailConfirmationToken)
    else:
        emailUserWelcomeConfirmation(userNew.Email, "https://" + os.environ['URL_APP'] + "/confirme-seu-email/"+userNew.EmailConfirmationToken)
    
    db.session.commit()
    return "Sua conta foi criada! Valide ela com o e-mail que enviamos.", HttpCode.SUCCESS

# Rota utilizada no primeiro acesso do jogador(quando ele informa nome, sobrenome, celular...)
@bp_user_login.route("/AddUserInfo", methods=["POST"])
def AddUserInfo():
    if not request.json:
        abort(HttpCode.ABORT)

    tokenReq = request.json.get('AccessToken')
    firstNameReq = request.json.get('FirstName')
    lastNameReq = request.json.get('LastName')
    phoneNumberReq = request.json.get('PhoneNumber')
    idCityReq = request.json.get('IdCity')
    idSportReq = request.json.get('IdSport')

    #para o caso especifico de o usuario entrar com conta apple a não compartilhar o email. 
    #Nesse caso temos q pedir o email no oboarding
    emailReq = request.json.get('Email')

    #Verifica se a cidade existe
    cidade = db.session.query(City).filter(City.IdCity == idCityReq).first()
    if cidade is None:
        return "Cidade inválida", HttpCode.WARNING

    #Verifica se o esporte existe
    esporte = db.session.query(Sport).filter(Sport.IdSport == idSportReq).first()
    if esporte is None:
        return "Esporte inválido", HttpCode.WARNING
    
    user = db.session.query(User).filter(User.AccessToken == tokenReq).first()

    #Verifica se o token é 0 ou null
    if tokenReq == 0 or tokenReq is None:
        return "Token inválido, faça login novamente", HttpCode.EXPIRED_TOKEN

    if not user:
        return "Token expirado", HttpCode.EXPIRED_TOKEN

    user.FirstName = firstNameReq.title()
    user.LastName = lastNameReq.title()
    user.PhoneNumber = phoneNumberReq
    user.IdCity = idCityReq
    user.IdSport = idSportReq
    user.IdGenderCategory = 3
    user.IdSidePreferenceCategory = 4
    
    if emailReq is not None:
        emailInUse = db.session.query(User).filter(User.Email == emailReq).first()
        if emailInUse is not None:
            return "Já existe uma conta com esse email", HttpCode.WARNING
        else:
            user.Email = emailReq

    rankCategories = db.session.query(RankCategory).all()

    for rankCategory in rankCategories:
        if rankCategory.RankSportLevel == 0:
            userRank = UserRank(
                IdUser = user.IdUser,
                IdRankCategory = rankCategory.IdRankCategory,
            )
            db.session.add(userRank)

    response = createCustomer(user)

    user.AsaasId = response.json().get('id')
    user.AsaasCreationDate = response.json().get('dateCreated')

    if response.status_code != 200:
        return "Tivemos um problema para criar sua conta. Tente novamente", HttpCode.WARNING
   
    db.session.commit()

    return jsonify({'User':user.to_json()}), HttpCode.SUCCESS

#Essa rota é utilizada pelo jogador quando inicializa o app. Caso tenha armazenado no cel algum AccessToken, ele envia pra essa rota e valida ele.
#Se estiver válido ele entra no app sem ter q digitar email e senha e atualiza o accessToken.
# Ele vai ser inválido quando, por exemplo, um jogador fizer login num cel A e depois num cel B. O AccessToken do cel A vai estar desatualizado.
##135 Com o Sandfriends Jogador Web, não é mais preciso ter token. Pode ser que envie ou não
@bp_user_login.route("/ValidateTokenUser", methods=["POST"])
def ValidateTokenUser():
    if not request.json:
        abort(HttpCode.ABORT)

    isTeacherReq = request.json.get('IsTeacher')
    tokenReq = request.json.get('AccessToken')
    requiresUserToProceedReq = request.json.get('RequiresUserToProceed')

   
    user = None

    if tokenReq is None:
        return "Token expirado", HttpCode.EXPIRED_TOKEN

    user = db.session.query(User).filter(User.AccessToken == tokenReq).first()
    
    if user is None and requiresUserToProceedReq == True:
        return 'Usuário não encontrado', HttpCode.WARNING

    if user.IsTeacher is None:
        user.IsTeacher = False
    
    if user.IsTeacher != isTeacherReq:
        if isTeacherReq:
            return "Você já utilizou esse e-mail para uma conta jogador. Crie uma nova conta com outro e-mail.",HttpCode.WARNING
        else:
            return "Você já utilizou esse e-mail para uma conta professor. Crie uma nova conta com outro e-mail.",HttpCode.WARNING
            
    if user is not None: 
        payloadUserId = DecodeToken(tokenReq)
        
        newToken = EncodeToken(payloadUserId)
        user.AccessToken = newToken
        db.session.commit()

    return initUserLoginData(user), HttpCode.SUCCESS

#Rota utilizada quando o jogador faz login com usuário e senha
@bp_user_login.route("/LoginUser", methods=["POST"])
def LoginUser():
    if not request.json:
        abort(HttpCode.ABORT)

    emailReq = request.json.get('Email')
    passwordReq = request.json.get('Password').encode('utf-8')
    isTeacherReq = request.json.get('IsTeacher')

    user = User.query.filter_by(Email = emailReq).first()

    if not user:
        return 'E-mail não cadastrado', HttpCode.WARNING
    
    if user.DateDisabled is not None:
        return "Não foi possível fazer login pois sua conta já foi excluída", HttpCode.WARNING
    
    if user.IsTeacher is None:
        user.IsTeacher = False
    
    if user.IsTeacher != isTeacherReq:
        if isTeacherReq:
            return "Você já utilizou esse e-mail para uma conta jogador. Crie uma nova conta com outro e-mail.",HttpCode.WARNING
        else:
            return "Você já utilizou esse e-mail para uma conta professor. Crie uma nova conta com outro e-mail.",HttpCode.WARNING

    if user.ThirdPartyLogin:
        if user.AppleToken is not None:
            return "Este e-mail foi cadastrado com uma conta Apple", HttpCode.ALERT
        else:
            return "Este e-mail foi cadastrado com uma conta do Google - Realize o login através do Google", HttpCode.ALERT

    #if user.Password != passwordReq:
    if not bcrypt.checkpw(passwordReq, (user.Password).encode('utf-8')):
        return 'Senha Incorreta', HttpCode.WARNING

    if user.EmailConfirmationDate == None:
        return "A sua conta ainda não foi validada - Siga as instruções no seu e-mail", HttpCode.WARNING

    #Senha correta e e-mail validado
    newToken = EncodeToken(user.IdUser)

    user.AccessToken = newToken
    db.session.commit()
        
    return initUserLoginData(user), HttpCode.SUCCESS

#Rota utilizada quando o jogador faz autenticação através de Third Party
#Pode realizar login ou cadastro
### TODO Receber um token do google - evitar que pessoas usem esta rota "sozinha"
### Poderia cadastrar um e-mail só rodando o /ThirdPartyAuthUser
### Esta rota não tem nenhum WARNING
@bp_user_login.route("/ThirdPartyAuthUser", methods=["POST"])
def ThirdPartyAuthUser():
    if not request.json:
        abort(HttpCode.ABORT)

    emailReq = request.json.get('Email')
    isTeacherReq = request.json.get('IsTeacher')

    user = User.query.filter(User.Email == emailReq).first()

    appleToken = request.json.get('AppleToken')

    #Ainda não estava cadastrado - realizar cadastro
    if not user: 
        if appleToken is not None:
            user = User.query.filter(User.AppleToken == appleToken).first()
        if user is None:
            user = User(
            Email = emailReq,
            Password = '',
            AccessToken = 0,
            RegistrationDate = datetime.now(),
            EmailConfirmationDate = datetime.now(),
            ThirdPartyLogin = True,
            AppleToken = appleToken,
            )

            db.session.add(user)
            db.session.flush()
            db.session.refresh(user)

        user.AccessToken = EncodeToken(user.IdUser)
        db.session.commit()
        return initUserLoginData(user), HttpCode.SUCCESS
    
    if user.AppleToken is not None:
        if user.AppleToken != appleToken:
            return "Não foi possível vincular sua conta apple. Contate nossa equipe para ajuda.", HttpCode.WARNING
    if user.IsTeacher is None:
        user.IsTeacher = False
        
    if user.IsTeacher != isTeacherReq:
        if isTeacherReq:
            return "Você já utilizou esse e-mail para uma conta jogador. Crie uma nova conta com outro e-mail.",HttpCode.WARNING
        else:
            return "Você já utilizou esse e-mail para uma conta professor. Crie uma nova conta com outro e-mail.",HttpCode.WARNING

    #Usuário já estava cadastrado - realizar login
    newToken = EncodeToken(user.IdUser)

    user.AccessToken = newToken
    db.session.commit()
    
    return initUserLoginData(user), HttpCode.SUCCESS

#Rota utilizada pelo jogador quando ele clica no link pra confirmação do email
@bp_user_login.route("/EmailConfirmationUser", methods=["POST"])
def EmailConfirmationUser():
    if not request.json:
        abort(HttpCode.ABORT)

    emailConfirmationTokenReq = request.json.get('EmailConfirmationToken')
    user = User.query.filter_by(EmailConfirmationToken=emailConfirmationTokenReq).first()
    if user:
        #Caso não esteja confirmado ainda
        if user.EmailConfirmationDate == None:
            user.EmailConfirmationDate = datetime.now()
            db.session.commit()
            return  {"AccessToken": user.AccessToken}, HttpCode.SUCCESS
        #Já estava confirmado
        else:
            return  "Sua conta já está válida", HttpCode.ALERT
    
    #Token não localizado
    return "Algo deu errado, tente novamente.", HttpCode.WARNING

#rota utilizada pelo jogador quando ele solicita para troca a senha. Nesse caso é enviado somente o email. Se o email estiver no banco do dados, é enviado um link para troca
@bp_user_login.route("/ChangePasswordRequestUser", methods=["POST"])
def ChangePasswordRequestUser():
    if not request.json:
        abort(HttpCode.ABORT)

    emailReq = request.json.get('Email')

    user = User.query.filter_by(Email=emailReq).first()

    if not user:
        return 'E-mail não cadastrado', HttpCode.WARNING

    #E-mail ainda não confirmado
    if user.EmailConfirmationDate == None:
        return "Você ainda não validou seu e-mail. Valide ele antes de trocar de senha", HttpCode.WARNING

    #E-mail já  confirmado
    user.ResetPasswordToken = str(datetime.now().timestamp()) + user.AccessToken
    db.session.commit()
    emailUserChangePassword(user.Email, user.FirstName, "https://" + os.environ['URL_APP'] + "/troca-senha/"+user.ResetPasswordToken)

    return 'Enviamos um e-mail para ser feita a troca de senha', HttpCode.SUCCESS

#rota acessada depois do usuario clicar no link para validar a troca de senha
@bp_user_login.route("/ValidateChangePasswordTokenUser", methods=["POST"])
def ValidateChangePasswordTokenUser():
    if not request.json:
        abort(HttpCode.ABORT)

    changePasswordTokenReq = request.json.get('ChangePasswordToken')

    user = User.query.filter_by(ResetPasswordToken=changePasswordTokenReq).first()
    
    if changePasswordTokenReq == 0 or changePasswordTokenReq is None:
        return webResponse("Não foi possível realizar a sua solicitação.", None), HttpCode.WARNING
    
    #Token não localizado
    if not user:
        return webResponse("Não foi possível realizar a sua solicitação.", None), HttpCode.WARNING

    return "Token válido.", HttpCode.SUCCESS
    

#rota utilizada pela jogador para alterar a senha
@bp_user_login.route("/ChangePasswordUser", methods=["POST"])
def ChangePasswordUser():
    if not request.json:
        abort(HttpCode.ABORT)

    changePasswordTokenReq = request.json.get('ChangePasswordToken')
    newPasswordReq = request.json.get('NewPassword').encode('utf-8')

    user = User.query.filter_by(ResetPasswordToken=changePasswordTokenReq).first()

    if changePasswordTokenReq == 0 or changePasswordTokenReq is None:
        return webResponse("Não foi possível realizar a sua solicitação.", None), HttpCode.WARNING

    if not user:
        return webResponse("Não foi possível realizar a sua solicitação.", None), HttpCode.WARNING

    #Caso tudo ok
    user.Password = bcrypt.hashpw(newPasswordReq, bcrypt.gensalt())
    user.ResetPasswordToken = None
    user.AccessToken = EncodeToken(user.IdUser)
    db.session.commit()
    return jsonify({"AccessToken":user.AccessToken}), HttpCode.SUCCESS

#Rota utilizada pelo jogador depois de fazer login e entrar na home do app. Aqui sãao requisitadas todas pertidas, recompensas, mensalistas... do jogador
@bp_user_login.route("/GetUserInfo", methods=["POST"])
def GetUserInfo():
    if not request.json:
        abort(HttpCode.ABORT)

    tokenReq = request.json.get('AccessToken')

    user = User.query.filter_by(AccessToken = tokenReq).first()

    #Verifica se o token é 0 ou null
    if tokenReq == 0 or tokenReq is None:
        return "Token inválido, faça login novamente", HttpCode.EXPIRED_TOKEN

    if user is None:
        return 'Token inválido.', HttpCode.EXPIRED_TOKEN

    updateNotificationsReq = request.json.get('UpdateNotifications')
    allowNotificationsReq = request.json.get('AllowNotifications')
    notificationsTokenReq = request.json.get('NotificationsToken')

    #apenas para preencher o notificationsOpenMatch e notificationsDiscount
    if user.AllowNotificationsOpenMatches is None:
        user.AllowNotificationsOpenMatches = user.AllowNotifications
    if user.AllowNotificationsCoupons is None:
        user.AllowNotificationsCoupons = user.AllowNotifications

    if updateNotificationsReq:
        user.AllowNotifications = allowNotificationsReq
    if notificationsTokenReq != "":
        user.NotificationsToken = notificationsTokenReq
    
    matchCounterList = getMatchCounterList(user)

    #Sobre a query
    #Busca todas partidas em aberto para o jogador, com base em sua cidade e esporte favorito cadastrados.
    #obs: aqui não precisa filtrar só por partidas em q o pagamento não expirou pq para abrir uma partida ele já verifica
    openMatches = db.session.query(Match)\
                .join(StoreCourt, StoreCourt.IdStoreCourt == Match.IdStoreCourt)\
                .join(Store, Store.IdStore == StoreCourt.IdStore)\
                .filter(Match.OpenUsers == True)\
                .filter((Match.Date > datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.IdTimeBegin >= int(datetime.now().strftime("%H")))))\
                .filter(Match.Canceled == False)\
                .filter(Match.IdSport == user.IdSport)\
                .filter(Store.IdCity == user.IdCity).all()
    
    openMatchesList = []
    #esse loop é feitor para contar as partidas da query acima em que o usuario não está dentro
    for openMatch in openMatches:
        userAlreadyInMatch = False
        matchMemberCounter = 0
        for member in openMatch.Members:
            if (member.User.IdUser == user.IdUser)  and (member.Refused == False) and (member.Quit == False):
                userAlreadyInMatch = True
                break
        if (userAlreadyInMatch == False) and (matchMemberCounter < openMatch.MaxUsers):
            openMatchesList.append(openMatch.to_json())

    userMatchesList = []
    #query para as partidas que o jogador jogou e vai jogar
    userMatches =  db.session.query(Match)\
                .join(MatchMember, Match.IdMatch == MatchMember.IdMatch)\
                .filter(MatchMember.IdUser == user.IdUser)\
                .filter((Match.Date > datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.IdTimeBegin >= int(datetime.now().strftime("%H"))))).all()

    for userMatch in userMatches:
        userMatchesList.append(userMatch.to_json())
    
    userRecurrentMatchesList = []
    #query para os mensalistas que do jogador
    userRecurrentMatches =  db.session.query(RecurrentMatch)\
                .filter(RecurrentMatch.IdUser == user.IdUser)\
                .filter(RecurrentMatch.IsExpired == False)\
                .filter(RecurrentMatch.Canceled == False).all()

    userRecurrentMatchesList = [recurrentMatch.to_json() for recurrentMatch in userRecurrentMatches if recurrentMatch.isPaymentExpired == False]

    notificationList = []
    notifications = db.session.query(NotificationUser).filter(NotificationUser.IdUser == user.IdUser).all()
    
    for notification in notifications:
        notificationList.append(notification.to_json())
        notification.Seen = True

    #não remover esse commit, ta salvando as permissões de push notifications
    db.session.commit()

    creditCards = db.session.query(UserCreditCard)\
            .filter(UserCreditCard.IdUser == user.IdUser)\
            .filter(UserCreditCard.Deleted == False).all()
    
    userCreditCardsList = []
    for creditCard in creditCards:
        userCreditCardsList.append(creditCard.to_json())


    return  jsonify({
        'UserMatches': userMatchesList, 
        'UserRecurrentMatches':  userRecurrentMatchesList,
        'OpenMatches': openMatchesList, 
        'Notifications': notificationList, 
        'UserRewards': RewardStatus(user.IdUser), 
        'MatchCounter': matchCounterList, 
        'CreditCards': userCreditCardsList}), 200


#Rota utilizada pelo professor depois de fazer login e entrar na home do app.
@bp_user_login.route("/GetTeacherInfo", methods=["POST"])
def GetTeacherInfo():
    if not request.json:
        abort(HttpCode.ABORT)

    tokenReq = request.json.get('AccessToken')

    user = User.query.filter_by(AccessToken = tokenReq)\
                    .filter_by(IsTeacher = True).first()

    #Verifica se o token é 0 ou null
    if tokenReq == 0 or tokenReq is None:
        return "Token inválido, faça login novamente", HttpCode.EXPIRED_TOKEN

    if user is None:
        return 'Token inválido.', HttpCode.EXPIRED_TOKEN

    updateNotificationsReq = request.json.get('UpdateNotifications')
    allowNotificationsReq = request.json.get('AllowNotifications')
    notificationsTokenReq = request.json.get('NotificationsToken')

    if updateNotificationsReq:
        user.AllowNotifications = allowNotificationsReq
    if notificationsTokenReq != "":
        user.NotificationsToken = notificationsTokenReq

    teacherRecurrentMatchesList = []
    #query para os mensalistas que do jogador
    teacherRecurrentMatches =  db.session.query(RecurrentMatch)\
                .filter(RecurrentMatch.IdUser == user.IdUser)\
                .filter(RecurrentMatch.IsExpired == False)\
                .filter(RecurrentMatch.Canceled == False).all()

    teacherRecurrentMatchesList = [recurrentMatch.to_json() for recurrentMatch in teacherRecurrentMatches if recurrentMatch.isPaymentExpired == False]

    #query das partidas do professor. Pegar todas as partidas do mês atual contando a semana atual.
    #ex: se em um mês dia 31 fosse quarta, eu ainda preciso do resto da semana (quinta, sex, sab e dom), mesmo q sejam de outro mes
    startDate = lastSundayOnLastMonth(datetime.today())
    endDate = firstSundayOnNextMonth(datetime.today())

    teacherMatches =  db.session.query(Match)\
                .join(MatchMember, Match.IdMatch == MatchMember.IdMatch)\
                .filter(MatchMember.IdUser == user.IdUser)\
                .filter((Match.Date > startDate) & (Match.Date < endDate)).all()

    matchList =[]
    for match in teacherMatches:
        matchList.append(match.to_json())

    notificationList = []
    notifications = db.session.query(NotificationUser).filter(NotificationUser.IdUser == user.IdUser).all()
    
    for notification in notifications:
        notificationList.append(notification.to_json())
        notification.Seen = True

    db.session.commit()
    
    return  jsonify({'Teacher': user.to_json_teacher(),\
                    'RecurrentMatches': teacherRecurrentMatchesList,\
                    'Matches':matchList,\
                    'Notifications': notificationList, \
                    'MatchesStartDate': startDate.strftime("%d/%m/%Y"),\
                    'MatchesEndDate': endDate.strftime("%d/%m/%Y"),}), HttpCode.SUCCESS
    
#Rota utilizada para excluir a conta do jogador
@bp_user_login.route("/RemoveUser", methods=["POST"])
def RemoveUser():
    if not request.json:
        abort(HttpCode.ABORT)

    tokenReq = request.json.get('AccessToken')

    user = User.query.filter_by(AccessToken = tokenReq).first()
    
    #Verifica se o token é 0 ou null
    if tokenReq == 0 or tokenReq is None:
        return "Token inválido, faça login novamente", HttpCode.EXPIRED_TOKEN

    if user is None:
        return 'Token inválido.', HttpCode.EXPIRED_TOKEN

    #Exclui o usuário do banco de dados
    user.AccessToken = None
    email = user.Email
    user.Email = user.Email + ".Deleted"
    user.DateDisabled = datetime.now()

    db.session.commit()
        
    return "O seu usuário foi excluído com sucesso", HttpCode.ALERT

def initUserLoginData(user):
    sports = db.session.query(Sport).all()
    sportsList = []
    for sport in sports:
        sportsList.append(sport.to_json())

    genders = db.session.query(GenderCategory).all()
    gendersList = []
    for gender in genders:
        gendersList.append(gender.to_json())

    sidePreferences = db.session.query(SidePreferenceCategory).all()
    sidePreferencesList = []
    for sidePreference in sidePreferences:
        sidePreferencesList.append(sidePreference.to_json())

    ranks = db.session.query(RankCategory).all()
    ranksList = []
    for rank in ranks:
        ranksList.append(rank.to_json())

    hours = db.session.query(AvailableHour).all()
    hoursList = []
    for hour in hours:
        hoursList.append(hour.to_json())
    
    infrastructures = db.session.query(InfrastructureCategory).all()
    infrastructureList = []
    for infrastructure in infrastructures:
        infrastructureList.append(infrastructure.to_json())

    userJson = None
    if user is not None:
        userJson = user.to_json()

    return jsonify({'States':GetAvailableCitiesList(), 'Sports':sportsList, 'Genders': gendersList, 'SidePreferences': sidePreferencesList, 'Ranks': ranksList, 'Hours': hoursList, 'Infrastructures': infrastructureList, 'User': userJson})

def getMatchCounterList(user):
    #Como o num de jogos do jogador não está e não pode ser obtida na tabela User ou UserLogin, tive q fazer a query manualmente(abaixo)
    #Sobre a query:
    #Aquele join é feito para relacionar a tabela Match com a tabela MatchMember, pq é na MatchMember que da pra verificar quais partidas o usuário jogou
    #São feitos vários filtros, como de data(só contabiliza jogos que já ocorreram), "WaitingApproval" (para não contabilizar caso o jogador não tenha aceitado a partida)
    #"Refused" (caso tenha recusado), "Quit" (caso tenha saido da partida) e "Canceled" (caso a partida tenha sido cancelada)
    matchCounterList=[]
    matchCounter = db.session.query(Match)\
        .join(MatchMember, MatchMember.IdMatch == Match.IdMatch)\
        .filter(MatchMember.IdUser == user.IdUser)\
        .filter(MatchMember.WaitingApproval == False)\
        .filter(MatchMember.Refused == False)\
        .filter(MatchMember.Quit == False)\
        .filter(Match.Canceled == False)\
        .filter((Match.Date < datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.IdTimeEnd <= datetime.now().hour))).all()

    sports = db.session.query(Sport).all()

    #contabiliza o num de partidas do jogador para cada esporte
    for sport in sports:
        matchCounterList.append({
            'Sport': sport.to_json(),
            'MatchCounter': len([match for match in matchCounter if match.IdSport == sport.IdSport])
        })
    
    return matchCounterList

#Usado para gerar o token de confirmação do e-mail
def generateRandomString(length):
    characters = string.ascii_lowercase + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string