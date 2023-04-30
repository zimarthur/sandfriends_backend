from flask import Blueprint, jsonify, abort, request
from datetime import datetime
import random
from sqlalchemy import null, true, ForeignKey
from ..routes.reward_routes import RewardStatus

from ..Models.user_model import User
from ..Models.store_model import Store
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
from ..Models.match_member_model import MatchMember
from ..routes.match_routes import getHourString
from ..Models.notification_model import Notification
from ..Models.notification_category_model import NotificationCategory
from ..extensions import db
from ..emails import sendEmail
from ..Models.http_codes import HttpCode
from ..access_token import EncodeToken, DecodeToken

#### TODO: Atualizar comentários desta rota

bp_user_login = Blueprint('bp_user_login', __name__)

# Rota para cadastrar jogador
@bp_user_login.route("/AddUser", methods=["POST"])
def AddUser():
    if not request.json:
        abort(HttpCode.ABORT)

    emailReq = request.json.get('Email')
    passwordReq = request.json.get('Password')
    time = datetime.now()

    user = User.query.filter_by(Email=emailReq).first()

    #Criar usuário novo
    if not user:        
        userNew = User(
            Email = emailReq,
            Password = passwordReq,
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
        sendEmail("https://www.sandfriends.com.br/emcf?str=0&tk="+userNew.EmailConfirmationToken)
        db.session.commit()
        return "Usuário criado com sucesso", HttpCode.SUCCESS
        #return userNew.to_json(), HttpCode.SUCCESS
    
    #O email que o usuário tentou cadastrar já foi cadastrado com o "Login com o google"
    if user.ThirdPartyLogin: 
        return "E-mail já cadastrado com uma conta Google",HttpCode.ALERT
    
    return "Este e-mail já foi cadastrado anteriormente",HttpCode.ALERT

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


#Essa rota é utilizada pelo jogador quando inicializa o app. Caso tenha armazenado no cel algum AccessToken, ele envia pra essa rota e valida ele.
#Se estiver válido ele entra no app sem ter q digitar email e senha e atualiza o accessToken.
# Ele vai ser invalido quando, por exemplo, um jogador fizer login num cel A e depois num cel B. O AccessToken do cel A vai estar desatualizado.
@bp_user_login.route("/ValidateToken", methods=["POST"])
def ValidateToken():
    if not request.json:
        abort(HttpCode.ABORT)
    token = request.json.get('AccessToken')

    payloadUserId = DecodeToken(token)
    user = User.query.filter_by(AccessToken = token).first()

    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN
    else:
        newToken = EncodeToken(payloadUserId)
        user.AccessToken = newToken
        db.session.commit()

        if user.User == None:
            return jsonify({'User': user.to_json()}), HttpCode.SUCCESS
        
        #nesse ponto, o AccessToken estava válido. Além de retornar ao jogador o novo accessToken,  ele envia tb as infos do jogador e o numero de jogos do jogador
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
            
        return jsonify({'User': user.to_json(), 'MatchCounter':matchCounterList}), HttpCode.SUCCESS

#Rota utilizada quando o jogador faz login com usuário e senha
@bp_user_login.route("/LoginUser", methods=["POST"])
def LoginUser():
    if not request.json:
        abort(HttpCode.ABORT)

    emailReq = request.json.get('Email')
    passwordReq = request.json.get('Password')

    user = User.query.filter_by(Email=emailReq).first()

    if not user:
        return 'E-mail não cadastrado', HttpCode.WARNING
    
    if user.ThirdPartyLogin:
        return "Este e-mail foi cadastrado com uma conta do Google - Realize o login através do Google", HttpCode.ALERT

    if user.Password != passwordReq:
        return 'Senha Incorreta', HttpCode.WARNING

    if user.EmailConfirmationDate == None:
        return "O seu e-mail ainda não foi validado - Siga as instruções no seu e-mail", HttpCode.WARNING

    #Senha correta e e-mail validado
    newToken = EncodeToken(user.IdUser)

    user.AccessToken = newToken
    db.session.commit()

    #Primeiro acesso do usuário - Redirecionar para tela de boas vindas
    if user.FirstName == None:
        return jsonify({'User': user.to_json()}), HttpCode.SUCCESS
    
    #mesma query do ValidateToken(interessante no futuro criar uma função pra não repetir codigo)
    # matchCounterList=[]
    # matchCounter = db.session.query(Match)\
    #     .join(MatchMember, MatchMember.IdMatch == Match.IdMatch)\
    #     .filter(MatchMember.IdUser == user.IdUser)\
    #     .filter(MatchMember.WaitingApproval == False)\
    #     .filter(MatchMember.Refused == False)\
    #     .filter(MatchMember.Quit == False)\
    #     .filter(Match.Canceled == False)\
    #     .filter((Match.Date < datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.IdTimeEnd <= datetime.now().hour))).all()

    # sports = db.session.query(Sport).all()

    # for sport in sports:
    #     matchCounterList.append({
    #         'Sport': sport.to_json(),
    #         'MatchCounter': len([match for match in matchCounter if match.IdSport == sport.IdSport])
    #     })

    matchCounterList = getMatchCounterList(user)
        
    return jsonify({'User': user.to_json(), 'MatchCounter':matchCounterList,}), HttpCode.SUCCESS

#Rota utilizada quando o jogador faz autenticação através de Third Party
#Pode realizar login ou cadastro
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
        ThirdPartyLogin = True,
        )

        db.session.add(user)
        db.session.flush()
        db.session.refresh(user)

        user.AccessToken = EncodeToken(user.IdUser)
        db.session.commit()
        return jsonify({'User': user.to_json()}), HttpCode.SUCCESS
    
    #Usuário já estava cadastrado - realizar login
    newToken = EncodeToken(user.IdUser)

    user.AccessToken = newToken
    db.session.commit()

    #Caso o usuário tenha criado a conta e ainda não feito login pela primeira vez - cadastrado nome
    if user.FirstName == None:
        return jsonify({'User': user.to_json()}), HttpCode.SUCCESS
    
    #mesma query do ValidateToken(interessante no futuro criar uma função pra não repetir codigo)
    # matchCounterList=[]
    # matchCounter = db.session.query(Match)\
    #     .join(MatchMember, MatchMember.IdMatch == Match.IdMatch)\
    #     .filter(MatchMember.IdUser == user.IdUser)\
    #     .filter(MatchMember.WaitingApproval == False)\
    #     .filter(MatchMember.Refused == False)\
    #     .filter(MatchMember.Quit == False)\
    #     .filter(Match.Canceled == False)\
    #     .filter((Match.Date < datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.IdTimeEnd <= datetime.now().hour))).all()

    # sports = db.session.query(Sport).all()

    # for sport in sports:
    #     matchCounterList.append({
    #         'Sport': sport.to_json(),
    #         'MatchCounter': len([match for match in matchCounter if match.IdSport == sport.IdSport])
    #     })
    
    matchCounterList = getMatchCounterList(user)

    return jsonify({'User': user.to_json(), 'MatchCounter':matchCounterList,}), HttpCode.SUCCESS

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
    sendEmail("troca de senha <br/> https://www.sandfriends.com.br/cgpw?str=0&tk="+user.ResetPasswordToken)
    return 'Enviamos um e-mail para ser feita a troca de senha', HttpCode.SUCCESS

#rota utilizada pela jogador para alterar a senha
@bp_user_login.route("/ChangePasswordUser", methods=["POST"])
def ChangePasswordUser():
    if not request.json:
        abort(HttpCode.ABORT)

    ResetPasswordTokenReq = request.json.get('ResetPasswordToken')
    newPasswordReq = request.json.get('NewPassword')

    user = User.query.filter_by(ResetPasswordToken=ResetPasswordTokenReq).first()

    if not user:
        return "Não foi possível realizar a sua solicitação", HttpCode.WARNING

    #Caso tudo ok
    user.Password = newPasswordReq
    user.ResetPasswordToken = None
    db.session.commit()
    return "Sua senha foi alterada com sucesso", HttpCode.SUCCESS

#Rota utilizada pelo jogador depois de fazer login e entrar na home do app. Aqui sãao requisitadas todas pertidas, recompensas, mensalistas... do jogador
@bp_user_login.route("/GetUserInfo", methods=["POST"])
def GetUserInfo():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')

    user = User.query.filter_by(AccessToken = accessToken).first()

    if user is None:
        return 'INVALID_ACCESS_TOKEN', HttpCode.INVALID_ACCESS_TOKEN

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
    
    openMatchesCounter = 0
    #esse loop é feitor para contar as partidas da query acima em que o usuario não está dentro
    for openMatch in openMatches:
        userAlreadyInMatch = False
        matchMemberCounter = 0
        for member in openMatch.Members:
            if (member.User.IdUser == user.IdUser)  and (member.Refused == False) and (member.Quit == False):
                userAlreadyInMatch = True
                break
            else:
                if (member.WaitingApproval == False) and (member.Refused == False) and (member.Quit == False):
                    matchMemberCounter +=1
        if (userAlreadyInMatch == False) and (matchMemberCounter < openMatch.MaxUsers):
            openMatchesCounter +=1

    userMatchesList = []
    #query para as partidas que o jogador jogou e vai jogar
    userMatches =  db.session.query(Match)\
                .join(MatchMember, Match.IdMatch == MatchMember.IdMatch)\
                .filter(MatchMember.IdUser == user.IdUser).all()

    for userMatch in userMatches:
        userMatchesList.append(userMatch.to_json())



    notificationList = []
    notifications = db.session.query(Notification).filter(Notification.IdUser == user.IdUser).all()
    
    for notification in notifications:
        notificationList.append(notification.to_json())
        notification.Seen = True
        db.session.commit()

    return  jsonify({'UserMatches': userMatchesList, 'OpenMatchesCounter': openMatchesCounter, 'Notifications': notificationList, 'UserRewards': RewardStatus(user.IdUser)}), 200


#rota acessada depois do usuario clicar no link para validar o token
@bp_user_login.route("/ValidateChangePasswordTokenUser", methods=["POST"])
def ValidateChangePasswordTokenUser():
    if not request.json:
        abort(HttpCode.ABORT)

    ResetPasswordTokenReq = request.json.get('ChangePasswordToken')

#rota que envia infos basicas do app, tipo os esportes cadastrados, generos, ranks
@bp_user_login.route("/GetAppCategories", methods=["GET"])
def GetAppCategories():
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

    return  jsonify({'Sports':sportsList, 'Genders': gendersList, 'SidePreferences': sidePreferencesList, 'Ranks': ranksList}), 200

def getMatchCounterList(user):
#mesma query do ValidateToken(interessante no futuro criar uma função pra não repetir codigo)
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

    for sport in sports:
        matchCounterList.append({
            'Sport': sport.to_json(),
            'MatchCounter': len([match for match in matchCounter if match.IdSport == sport.IdSport])
        })
    
    return matchCounterList