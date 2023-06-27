from flask import Blueprint, jsonify, abort, request
from datetime import datetime
import random
from sqlalchemy import null, true, ForeignKey

from ..routes.reward_routes import RewardStatus
from ..responses import webResponse
from ..Models.user_model import User
from ..Models.store_model import Store
from ..Models.available_hour_model import AvailableHour
from ..Models.rank_category_model import RankCategory
from ..Models.gender_category_model import GenderCategory
from ..Models.side_preference_category_model import SidePreferenceCategory
from ..Models.store_photo_model import StorePhoto
from ..Models.store_court_model import StoreCourt
from ..Models.sport_model import Sport
from ..Models.city_model import City
from ..Models.state_model import State
from ..Models.user_rank_model import UserRank
from ..Models.match_model import Match
from ..Models.recurrent_match_model import RecurrentMatch
from ..Models.match_member_model import MatchMember
from ..routes.match_routes import getHourString
from ..Models.notification_user_model import NotificationUser
from ..Models.notification_user_category_model import NotificationUserCategory
from ..extensions import db
from ..emails import sendEmail
from ..Models.http_codes import HttpCode
from ..access_token import EncodeToken, DecodeToken
import bcrypt

bp_user_login = Blueprint('bp_user_login', __name__)

# Rota para cadastrar jogador
@bp_user_login.route("/AddUser", methods=["POST"])
def AddUser():
    if not request.json:
        abort(HttpCode.ABORT)

    emailReq = request.json.get('Email')
    passwordReq = request.json.get('Password').encode('utf-8')
    time = datetime.now()

    user = User.query.filter_by(Email=emailReq).first()

    #Criar usuário novo
    if user:
        #O email que o usuário tentou cadastrar já foi cadastrado com o "Login com o google"
        if user.ThirdPartyLogin: 
            return "E-mail já cadastrado com uma conta Google",HttpCode.ALERT

        return "Este e-mail já foi cadastrado anteriormente",HttpCode.WARNING

    userNew = User(
        Email = emailReq,
        Password = bcrypt.hashpw(passwordReq, bcrypt.gensalt()),
        AccessToken = 0, 
        RegistrationDate = time,
        ThirdPartyLogin = False,
    )

    #A etapa abaixo acontece porque o IdUser da tabela User é incrementado automaticamente.
    #Na hora que o novo usuário é inserido, não se sabe qual o IdUser dele. Por issso tem aquele .flush(), ele faz com que esse IdUser seja "calculado"
    db.session.add(userNew)
    db.session.flush()  
    db.session.refresh(userNew)
    
    #Com o IdUser já "calculado" já da pra criar o accessToken, que é feito no arquivo access_token.py, 
    #e criar o token pra confimação do email(que é enviado por email pela função sendEmail())
    userNew.AccessToken = EncodeToken(userNew.IdUser)
    userNew.EmailConfirmationToken = str(datetime.now().timestamp()) + userNew.AccessToken
    #emcf=email confirmation(não sei se é legal ter uma url explicita), str(pra distinguir se é store=1 ou user = 0)
    #tk = token
    sendEmail("https://quadras.sandfriends.com.br/emcf?str=0&tk="+userNew.EmailConfirmationToken)
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
    tokenNullOrZero(tokenReq)

    if not user:
        return "Token expirado", HttpCode.EXPIRED_TOKEN

    user.FirstName = firstNameReq.title()
    user.LastName = lastNameReq.title()
    user.PhoneNumber = phoneNumberReq
    user.IdCity = idCityReq
    user.IdSport = idSportReq

    db.session.commit()

    return jsonify({'User':user.to_json()}), HttpCode.SUCCESS

#Essa rota é utilizada pelo jogador quando inicializa o app. Caso tenha armazenado no cel algum AccessToken, ele envia pra essa rota e valida ele.
#Se estiver válido ele entra no app sem ter q digitar email e senha e atualiza o accessToken.
# Ele vai ser inválido quando, por exemplo, um jogador fizer login num cel A e depois num cel B. O AccessToken do cel A vai estar desatualizado.
@bp_user_login.route("/ValidateTokenUser", methods=["POST"])
def ValidateTokenUser():
    if not request.json:
        abort(HttpCode.ABORT)

    tokenReq = request.json.get('AccessToken')

    #Verifica se o token é 0 ou null
    tokenNullOrZero(tokenReq)
    
    user = db.session.query(User).filter(User.AccessToken == tokenReq).first()
    payloadUserId = DecodeToken(tokenReq)

    if user is None:
        return 'Usuário não encontrado', HttpCode.WARNING
    
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

    user = User.query.filter_by(Email = emailReq).first()

    if not user:
        return 'E-mail não cadastrado', HttpCode.WARNING
    
    if user.ThirdPartyLogin:
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

    user = User.query.filter_by(Email=emailReq).first()

    #Ainda não estava cadastrado - realizar cadastro
    if not user: 
        user = User(
        Email = emailReq,
        Password = '',
        AccessToken = 0,
        RegistrationDate = datetime.now(),
        EmailConfirmationDate = datetime.now(),
        ThirdPartyLogin = True,
        )

        db.session.add(user)
        db.session.flush()
        db.session.refresh(user)

        user.AccessToken = EncodeToken(user.IdUser)
        db.session.commit()
        return initUserLoginData(user), HttpCode.SUCCESS
    
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
            return "Sua conta foi validada com sucesso!", HttpCode.SUCCESS
        #Já estava confirmado
        else:
            return "Sua conta já está válida", HttpCode.ALERT
    
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
    sendEmail("troca de senha <br/> https://quadras.sandfriends.com.br/cgpw?str=0&tk="+user.ResetPasswordToken)
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
    db.session.commit()
    return webResponse("Sua senha foi alterada com sucesso", None), HttpCode.ALERT

#Rota utilizada pelo jogador depois de fazer login e entrar na home do app. Aqui sãao requisitadas todas pertidas, recompensas, mensalistas... do jogador
@bp_user_login.route("/GetUserInfo", methods=["POST"])
def GetUserInfo():
    if not request.json:
        abort(HttpCode.ABORT)

    tokenReq = request.json.get('AccessToken')

    user = User.query.filter_by(AccessToken = tokenReq).first()

    #Verifica se o token é 0 ou null
    tokenNullOrZero(tokenReq)

    if user is None:
        return 'Token inválido.', HttpCode.EXPIRED_TOKEN

    matchCounterList = getMatchCounterList(user)

    #Sobre a query
    #Busca todas partidas em aberto para o jogador, com base em sua cidade e esporte favorito cadastrados.
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

    for userRecurrentMatch in userRecurrentMatches:
        userRecurrentMatchesList.append(userRecurrentMatch.to_json())

    notificationList = []
    notifications = db.session.query(NotificationUser).filter(NotificationUser.IdUser == user.IdUser).all()
    
    for notification in notifications:
        notificationList.append(notification.to_json())
        notification.Seen = True
    db.session.commit()

    return  jsonify({'UserMatches': userMatchesList, 'UserRecurrentMatches':  userRecurrentMatchesList,'OpenMatches': openMatchesList, 'Notifications': notificationList, 'UserRewards': RewardStatus(user.IdUser), 'MatchCounter': matchCounterList}), 200

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

    return jsonify({'Sports':sportsList, 'Genders': gendersList, 'SidePreferences': sidePreferencesList, 'Ranks': ranksList, 'Hours': hoursList, 'User': user.to_json()})

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

def tokenNullOrZero(token):
    if token == 0 or token is None:
        return "Token inválido", HttpCode.EXPIRED_TOKEN