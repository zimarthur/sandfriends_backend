from flask import Blueprint, jsonify, abort, request
from datetime import datetime
import random
from sqlalchemy import null, true, ForeignKey
from ..routes.reward_routes import RewardStatus

from ..Models.user_login_model import UserLogin
from ..Models.store_model import Store
from ..Models.user_model import User
from ..Models.rank_category_model import RankCategory
from ..Models.gender_category_model import GenderCategory
from ..Models.side_preference_category_model import SidePreferenceCategory
from ..Models.store_photo_model import StorePhoto
from ..Models.store_court_model import StoreCourt
from ..Models.sport_model import Sport
from ..Models.city_model import City
from ..Models.state_model import State
from ..Models.user_model import User
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


bp_user_login = Blueprint('bp_user_login', __name__)



def IsNewUser(UserLogin):
    if UserLogin.User == None:
        return True
    else:
        return False


# Rota para cadastrar jogador
@bp_user_login.route("/SignIn", methods=["POST"])
def SignIn():
    if not request.json:
        abort(HttpCode.ABORT)

    email = request.json.get('Email')
    password = request.json.get('Password')
    time = datetime.now()

    user = UserLogin.query.filter_by(Email=email).first()

    #verifica se ja existe algum jogador com o email enviado
    if not user:        
        userLogin = UserLogin(
            Email = email,
            Password = password,
            AccessToken = 0, 
            RegistrationDate = time,
            ThirdPartyLogin = False,
        )

        #A etapa abaixo acontece porque o IdUser da tabela User e da tabela UserLogin é o mesmo, mas ele é incrementado automaticamente.
        #Na hora que o novo usuário é inserido, não se sabe qual o IdUser dele. Por issso tem aquele .flush(), ele faz com que esse IdUser seja "calculado"
        db.session.add(userLogin)
        db.session.flush()  
        db.session.refresh(userLogin)
        
        #Com o IdUser já "calculado" já da pra criar o accessToken, que é feito no arquivo access_token.py, 
        #e criar o token pra confimação do email(que é enviado por email pela função sendEmail())
        userLogin.AccessToken = EncodeToken(userLogin.IdUser)
        userLogin.EmailConfirmationToken = str(datetime.now().timestamp()) + userLogin.AccessToken
        sendEmail("https://www.sandfriends.com.br/redirect/?ct=emcf&bd="+userLogin.EmailConfirmationToken)
        db.session.commit()
        return userLogin.to_json(), HttpCode.SUCCESS
    else:
        if user.ThirdPartyLogin: #Nesse caso, o email que o usuário tentou cadastrar já foi cadastrado com o "Login com o google"
            return "e-mail já cadastrado com Conta Google",HttpCode.EMAIL_ALREADY_USED_THIRDPARTY
        else:
            if password == user.Password:
                if user.EmailConfirmationDate == None:
                    return "você já criou uma conta com esse e-mail. Valide ela com o link que enviamos.", HttpCode.WAITING_EMAIL_CONFIRMATION
                else:
                    return "sua conta já está ativa, faça login", HttpCode.ACCOUNT_ALREADY_CREATED
            else:
                return "e-mail já cadastrado",HttpCode.EMAIL_ALREADY_USED

#Rota utilizada pelo jogador quando ele clica no link pra confirmação do email
@bp_user_login.route("/ConfirmEmail", methods=["POST"])
def ConfirmEmail():
    if not request.json:
        abort(HttpCode.ABORT)

    emailConfirmationToken = request.json.get('EmailConfirmationToken')
    userLogin = UserLogin.query.filter_by(EmailConfirmationToken=emailConfirmationToken).first()
    if userLogin:
        if userLogin.EmailConfirmationDate == None:
            userLogin.EmailConfirmationDate = datetime.now()
            db.session.commit()
            return "ok", HttpCode.SUCCESS
        else:
            return "Already confirmed", HttpCode.EMAIL_ALREADY_CONFIRMED
    else:
        return "Wrong Token", HttpCode.INVALID_EMAIL_CONFIRMATION_TOKEN


#Essa rota é utilizada pelo jogador quando inicializa o app. Caso tenha armazenado no cel algum AccessToken, ele envia pra essa rota e valida ele.
#Se estiver válido ele entra no app sem ter q digitar email e senha e atualiza o accessToken.
# Ele vai ser invalido quando, por exemplo, um jogador fizer login num cel A e depois num cel B. O AccessToken do cel A vai estar desatualizado.
@bp_user_login.route("/ValidateToken", methods=["POST"])
def ValidateToken():
    if not request.json:
        abort(HttpCode.ABORT)
    token = request.json.get('AccessToken')

    payloadUserId = DecodeToken(token)
    userLogin = UserLogin.query.filter_by(AccessToken = token).first()

    if userLogin is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN
    else:
        newToken = EncodeToken(payloadUserId)
        userLogin.AccessToken = newToken
        db.session.commit()

        if userLogin.User == None:
            return jsonify({'UserLogin': userLogin.to_json()}), HttpCode.SUCCESS
        
        #nesse ponto, o AccessToken estava válido. Além de retornar ao jogador o novo accessToken,  ele envia tb as infos do jogador e o numero de jogos do jogador
        #Como o num de jogos do jogador não está e não pode ser obtida na tabela User ou UserLogin, tive q fazer a query manualmente(abaixo)
        #Sobre a query:
        #Aquele join é feito para relacionar a tabela Match com a tabela MatchMember, pq é na MatchMember que da pra verificar quais partidas o usuário jogou
        #São feitos vários filtros, como de data(só contabiliza jogos que já ocorreram), "WaitingApproval" (para não contabilizar caso o jogador não tenha aceitado a partida)
        #"Refused" (caso tenha recusado), "Quit" (caso tenha saido da partida) e "Canceled" (caso a partida tenha sido cancelada)
        matchCounterList=[]
        matchCounter = db.session.query(Match)\
            .join(MatchMember, MatchMember.IdMatch == Match.IdMatch)\
            .filter(MatchMember.IdUser == userLogin.IdUser)\
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
            
        return jsonify({'UserLogin': userLogin.to_json(), 'User': userLogin.User.to_json(), 'MatchCounter':matchCounterList}), HttpCode.SUCCESS

#Rota utilizada quando o jogador faz login
@bp_user_login.route("/LogIn", methods=["POST"])
def LogIn():
    if not request.json:
        abort(HttpCode.ABORT)
    
    email = request.json.get('Email')
    password = request.json.get('Password')
    thirdPartyLogin = request.json.get('ThirdPartyLogin') #quando o jogador clica para fazer login com o google, a propria API do google "valida" o jogador

    userLogin = UserLogin.query.filter_by(Email=email).first()

    if thirdPartyLogin:
        if not userLogin: #entrou com o google, mas ainda não estava cadastrado
            userLogin = UserLogin(
            Email = email,
            Password = '',
            AccessToken = 0, 
            RegistrationDate = datetime.now(),
            ThirdPartyLogin = True,
            )
            db.session.add(userLogin)
            db.session.flush()
            db.session.refresh(userLogin)

            userLogin.AccessToken = EncodeToken(userLogin.IdUser)
            db.session.commit()
            return jsonify({'UserLogin': userLogin.to_json()}), HttpCode.SUCCESS
        else:
            newToken = EncodeToken(userLogin.IdUser)

            userLogin.AccessToken = newToken
            db.session.commit()

            if userLogin.User == None:
                return jsonify({'UserLogin': userLogin.to_json()}), HttpCode.SUCCESS
            
            #mesma query do ValidateToken(interessante no futuro criar uma função pra não repetir codigo)
            matchCounterList=[]
            matchCounter = db.session.query(Match)\
                .join(MatchMember, MatchMember.IdMatch == Match.IdMatch)\
                .filter(MatchMember.IdUser == userLogin.IdUser)\
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
                
            return jsonify({'UserLogin': userLogin.to_json(), 'User': userLogin.User.to_json(), 'MatchCounter':matchCounterList,}), HttpCode.SUCCESS

    else:
        if not userLogin:
            return 'Esse email não está cadastrado', HttpCode.EMAIL_NOT_FOUND
        else:
            if userLogin.ThirdPartyLogin:
                return "e-mail já cadastrado com Conta Google",HttpCode.EMAIL_ALREADY_USED_THIRDPARTY
            else:
                if userLogin.Password == password:
                    if userLogin.EmailConfirmationDate != None:
                        newToken = EncodeToken(userLogin.IdUser)

                        userLogin.AccessToken = newToken
                        db.session.commit()

                        if userLogin.User == None:
                            return jsonify({'UserLogin': userLogin.to_json()}), HttpCode.SUCCESS
                        
                        #mesma query do ValidateToken(interessante no futuro criar uma função pra não repetir codigo)
                        matchCounterList=[]
                        matchCounter = db.session.query(Match)\
                            .join(MatchMember, MatchMember.IdMatch == Match.IdMatch)\
                            .filter(MatchMember.IdUser == userLogin.IdUser)\
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
                            
                        return jsonify({'UserLogin': userLogin.to_json(), 'User': userLogin.User.to_json(), 'MatchCounter':matchCounterList,}), HttpCode.SUCCESS

                    else:
                        return "valide email", HttpCode.WAITING_EMAIL_CONFIRMATION
                else:
                    return 'Senha Incorreta', HttpCode.INVALID_PASSWORD

#rota utilizada pelo jogador quando ele solicita para troca a senha. Nesse caso é enviado somente o email. Se o email estiver no banco do dados, é enviado um link para troca
@bp_user_login.route("/ChangePasswordRequest", methods=["POST"])
def ChangePasswordRequest():
    if not request.json:
        abort(HttpCode.ABORT)
    email = request.json.get('Email')

    userLogin = UserLogin.query.filter_by(Email=email).first()
    if not userLogin:
        return 'Esse email não está cadastrado', HttpCode.EMAIL_NOT_FOUND
    else:
        if userLogin.EmailConfirmationDate != None:
            userLogin.ResetPasswordValue = str(datetime.now().timestamp()) + userLogin.AccessToken
            db.session.commit()
            sendEmail("troca de senha <br/> https://www.sandfriends.com.br/redirect/?ct=cgpw&bd="+userLogin.ResetPasswordValue)
            return 'Code Sent', HttpCode.SUCCESS
        else:
            return "email not confirmed", HttpCode.WAITING_EMAIL_CONFIRMATION

#rota utilizada pela jogador para alterar a senha
@bp_user_login.route("/ChangePassword", methods=["POST"])
def ChangePassword():
    if not request.json:
        abort(HttpCode.ABORT)

    resetPasswordValue = request.json.get('ResetPasswordValue')
    newPassword = request.json.get('NewPassword')

    userLogin = UserLogin.query.filter_by(ResetPasswordValue=resetPasswordValue).first()
    if userLogin:
        userLogin.Password = newPassword
        userLogin.ResetPasswordValue = None
        db.session.commit()
        return "password changed", HttpCode.SUCCESS
    else:
        return "invalid ResetPasswordValue", HttpCode.INVALID_RESET_PASSWORD_VALUE

#Rota utilizada pelo jogador depois de fazer login e entrar na home do app. Aqui sãao requisitadas todas pertidas, recompensas, mensalistas... do jogador
@bp_user_login.route("/GetUserInfo", methods=["POST"])
def GetUserInfo():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')

    userLogin = UserLogin.query.filter_by(AccessToken = accessToken).first()

    if userLogin is None:
        return 'INVALID_ACCESS_TOKEN', HttpCode.INVALID_ACCESS_TOKEN

    #Sobre a query
    #Busca todas partidas em aberto para o jogador, com base em sua cidade e esporte favorito cadastrados.
    openMatches = db.session.query(Match)\
                .join(StoreCourt, StoreCourt.IdStoreCourt == Match.IdStoreCourt)\
                .join(Store, Store.IdStore == StoreCourt.IdStore)\
                .filter(Match.OpenUsers == True)\
                .filter((Match.Date > datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.IdTimeBegin >= int(datetime.now().strftime("%H")))))\
                .filter(Match.Canceled == False)\
                .filter(Match.IdSport == userLogin.User.IdSport)\
                .filter(Store.IdCity == userLogin.User.IdCity).all()
    
    openMatchesCounter = 0
    #esse loop é feitor para contar as partidas da query acima em que o usuario não está dentro
    for openMatch in openMatches:
        userAlreadyInMatch = False
        matchMemberCounter = 0
        for member in openMatch.Members:
            if (member.User.IdUser == userLogin.IdUser)  and (member.Refused == False) and (member.Quit == False):
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
                .filter(MatchMember.IdUser == userLogin.IdUser).all()

    for userMatch in userMatches:
        userMatchesList.append(userMatch.to_json())



    notificationList = []
    notifications = db.session.query(Notification).filter(Notification.IdUser == userLogin.IdUser).all()
    
    for notification in notifications:
        notificationList.append(notification.to_json())
        notification.Seen = True
        db.session.commit()

    return  jsonify({'UserMatches': userMatchesList, 'OpenMatchesCounter': openMatchesCounter, 'Notifications': notificationList, 'UserRewards': RewardStatus(userLogin.IdUser)}), 200



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
