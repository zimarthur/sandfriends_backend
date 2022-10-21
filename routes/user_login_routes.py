from flask import Blueprint, jsonify, abort, request
from datetime import datetime
import random

from sqlalchemy import null, true, ForeignKey

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



def IsNewUser(UserId):
    filledUser = User.query.filter_by(IdUser=UserId).first()
    if filledUser == None:
        return True
    else:
        return False

def SendEmailConfirmation(User):
    return True
    
@bp_user_login.route("/ValidateToken", methods=["POST"])
def ValidateToken():
    if not request.json:
        abort(HttpCode.ABORT)
    token = request.json.get('AccessToken')

    payloadUserId = DecodeToken(token)
    userLogin = UserLogin.query.filter_by(AccessToken = token).first()
    if userLogin is None:
        userLogin = UserLogin.query.filter_by(IdUser = payloadUserId).first()
        if userLogin is None:
            return '2', HttpCode.INVALID_USER_ID
        else:
            return '1', HttpCode.INVALID_ACCESS_TOKEN
    else:
        newToken = EncodeToken(payloadUserId)

        login = {
            'AccessToken': newToken,
            'IsNewUser': IsNewUser(payloadUserId),
            'EmailConfirmationDate':userLogin.EmailConfirmationDate,
            'Email': userLogin.Email
        }

        userLogin.AccessToken = newToken
        db.session.commit()

        if IsNewUser(userLogin.IdUser):
            return jsonify({'login': login}), HttpCode.SUCCESS

        user = db.session.query(User).filter_by(IdUser = userLogin.IdUser).first()

        userRanks = db.session.query(UserRank).filter_by(IdUser = user.IdUser).all()

        userRanksList = []
        for userRank in userRanks:
            userRanksList.append(userRank.to_json())
        
        matchCounterList=[]
        matchCounter = db.session.query(Match)\
            .join(MatchMember, MatchMember.IdMatch == Match.IdMatch)\
            .filter(MatchMember.IdUser == user.IdUser)\
            .filter(MatchMember.WaitingApproval == False)\
            .filter(MatchMember.Refused == False)\
            .filter(MatchMember.Quit == False)\
            .filter(Match.Canceled == False)\
            .filter((Match.Date < datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.TimeEnd <= datetime.now().hour))).all()

        sports = db.session.query(Sport).all()

        for sport in sports:
            matchCounterList.append({
                'idSport': sport.IdSport,
                'matchCounter': len([match for match in matchCounter if match.IdSport == sport.IdSport])
            })

        userCityJson = ""
        userStateJson = ""
        if user.IdCity != None:
            userCity = db.session.query(City).filter(City.IdCity == user.IdCity).first()
            userState = db.session.query(State).filter(State.IdState == userCity.IdState).first()
            userCityJson = userCity.to_json()
            userStateJson = userState.to_json()
            
        return jsonify({'login': login, 'user': user.to_json(), 'userRanks': userRanksList, 'matchCounter':matchCounterList, 'userEmail':userLogin.Email, 'userCity': userCityJson, 'userState': userStateJson}), HttpCode.SUCCESS

@bp_user_login.route("/SignIn", methods=["POST"])
def SignIn():
    if not request.json:
        abort(HttpCode.ABORT)

    email = request.json.get('Email')
    password = request.json.get('Password')
    time = datetime.now()

    user = UserLogin.query.filter_by(Email=email).first()
    if not user:        
        userLogin = UserLogin(
            Email = email,
            Password = password,
            AccessToken = 0, 
            RegistrationDate = time,
            ThirdPartyLogin = False,
        )
        db.session.add(userLogin)
        db.session.flush()
        db.session.refresh(userLogin)

        userLogin.AccessToken = EncodeToken(userLogin.IdUser)
        userLogin.EmailConfirmationToken = str(datetime.now().timestamp()) + userLogin.AccessToken
        sendEmail("https://www.sandfriends.com.br/redirect/?ct=emcf&bd="+userLogin.EmailConfirmationToken)
        db.session.commit()
        data ={
            'AccessToken': userLogin.AccessToken,
            'IsNewUser': True
        }
        return data, HttpCode.SUCCESS
    else:
        if user.ThirdPartyLogin:
            return "e-mail já cadastrado com Conta Google",HttpCode.EMAIL_ALREADY_USED_THIRDPARTY
        else:
            if password == user.Password:
                if user.EmailConfirmationDate == None:
                    return "você já criou uma conta com esse e-mail. Valide ela com o link que enviamos.", HttpCode.WAITING_EMAIL_CONFIRMATION
                else:
                    return "sua conta já está ativa, faça login", HttpCode.ACCOUNT_ALREADY_CREATED
            else:
                return "e-mail já cadastrado",HttpCode.EMAIL_ALREADY_USED

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


@bp_user_login.route("/LogIn", methods=["POST"])
def LogIn():
    if not request.json:
        abort(HttpCode.ABORT)
    
    email = request.json.get('Email')
    password = request.json.get('Password')
    thirdPartyLogin = request.json.get('ThirdPartyLogin')

    userLogin = UserLogin.query.filter_by(Email=email).first()

    if thirdPartyLogin:
        if not userLogin: #sign up with google new account
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
            login ={
            'AccessToken': userLogin.AccessToken,
            'IsNewUser': True
            }
        else:
            newToken = EncodeToken(userLogin.IdUser)
            login = {
            'AccessToken': newToken,
            'IsNewUser': IsNewUser(userLogin.IdUser)
            }
            userLogin.AccessToken = newToken
            db.session.commit()
        user = db.session.query(User).filter_by(IdUser = userLogin.IdUser).first()

        userRanks = db.session.query(UserRank).filter_by(IdUser = user.IdUser).all()

        userRanksList = []
        for userRank in userRanks:
            userRanksList.append(userRank.to_json())

        matchCounterList=[]
        matchCounter = db.session.query(Match)\
            .join(MatchMember, MatchMember.IdMatch == Match.IdMatch)\
            .filter(MatchMember.IdUser == user.IdUser)\
            .filter(MatchMember.WaitingApproval == False)\
            .filter(MatchMember.Refused == False)\
            .filter(MatchMember.Quit == False)\
            .filter(Match.Canceled == False)\
            .filter((Match.Date < datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.TimeEnd <= datetime.now().hour))).all()

        sports = db.session.query(Sport).all()

        for sport in sports:
            matchCounterList.append({
                'idSport': sport.IdSport,
                'matchCounter': len([match for match in matchCounter if match.IdSport == sport.IdSport])
            })

        userCityJson = ""
        userStateJson = ""
        if user.IdCity != None:
            userCity = db.session.query(City).filter(City.IdCity == user.IdCity).first()
            userState = db.session.query(State).filter(State.IdState == userCity.IdState).first()
            userCityJson = userCity.to_json()
            userStateJson = userState.to_json()

        return jsonify({'login': login, 'user': user.to_json(), 'userRanks': userRanksList, 'matchCounter': matchCounterList, 'userEmail':userLogin.Email, 'userCity': userCityJson, 'userState': userStateJson}), HttpCode.SUCCESS
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
                        login ={
                        'AccessToken': newToken,
                        'IsNewUser': IsNewUser(userLogin.IdUser)
                        }
                        userLogin.AccessToken = newToken
                        db.session.commit()

                        if IsNewUser(userLogin.IdUser):
                            return jsonify({'login': login}), HttpCode.SUCCESS

                        user = db.session.query(User).filter_by(IdUser = userLogin.IdUser).first()

                        userRanks = db.session.query(UserRank).filter_by(IdUser = user.IdUser).all()

                        userRanksList = []
                        for userRank in userRanks:
                            userRanksList.append(userRank.to_json())

                        matchCounterList=[]
                        matchCounter = db.session.query(Match)\
                            .join(MatchMember, MatchMember.IdMatch == Match.IdMatch)\
                            .filter(MatchMember.IdUser == user.IdUser)\
                            .filter(MatchMember.WaitingApproval == False)\
                            .filter(MatchMember.Refused == False)\
                            .filter(MatchMember.Quit == False)\
                            .filter(Match.Canceled == False)\
                            .filter((Match.Date < datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.TimeEnd <= datetime.now().hour))).all()

                        sports = db.session.query(Sport).all()

                        for sport in sports:
                            matchCounterList.append({
                                'idSport': sport.IdSport,
                                'matchCounter': len([match for match in matchCounter if match.IdSport == sport.IdSport])
                            })

                        userCityJson = ""
                        userStateJson = ""
                        if user.IdCity != None:
                            userCity = db.session.query(City).filter(City.IdCity == user.IdCity).first()
                            userState = db.session.query(State).filter(State.IdState == userCity.IdState).first()
                            userCityJson = userCity.to_json()
                            userStateJson = userState.to_json()
                        return jsonify({'login': login, 'user': user.to_json(), 'userRanks': userRanksList, 'matchCounter': matchCounterList, 'userEmail':userLogin.Email, 'userCity': userCityJson, 'userState': userStateJson}), HttpCode.SUCCESS
                    else:
                        return "valide email", HttpCode.WAITING_EMAIL_CONFIRMATION
                else:
                    return 'Senha Incorreta', HttpCode.INVALID_PASSWORD

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


@bp_user_login.route("/GetUserInfo", methods=["POST"])
def GetUserInfo():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')

    userLogin = UserLogin.query.filter_by(AccessToken = accessToken).first()

    if userLogin is None:
        return 'INVALID_ACCESS_TOKEN', HttpCode.INVALID_ACCESS_TOKEN

    userInfo = User.query.get(userLogin.IdUser)

    openMatches = db.session.query(Match)\
                .join(Store, Store.IdStore == Match.IdStore)\
                .filter(Match.OpenUsers == True)\
                .filter((Match.Date > datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.TimeBegin >= int(datetime.now().strftime("%H")))))\
                .filter(Match.Canceled == False)\
                .filter(Match.IdSport == userInfo.IdSport)\
                .filter(Store.City == userInfo.IdCity).all()
    
    openMatchMembers = db.session.query(MatchMember)\
                .filter(MatchMember.IdMatch.in_([match.IdMatch for match in openMatches]))\
                .filter(MatchMember.WaitingApproval == False)\
                .filter(MatchMember.Refused == False)\
                .filter(MatchMember.Quit == False).all()     

    openMatchesCounter = 0
    for match in openMatches:
        matchMembers = [member for member in openMatchMembers if member.IdMatch == match.IdMatch]
        if (len(matchMembers) < match.MaxUsers) and (any(member.IdUser == userInfo.IdUser for member in matchMembers) == False): 
            openMatchesCounter +=1

    userMatchesList = []

    userMatches =  db.session.query(Match, Sport, Store, StoreCourt)\
                .join(MatchMember, Match.IdMatch == MatchMember.IdMatch)\
                .join(Store, Store.IdStore == Match.IdStore)\
                .join(Sport, Sport.IdSport == Match.IdSport)\
                .join(StoreCourt, StoreCourt.IdStoreCourt == Match.IdStoreCourt)\
                .filter(MatchMember.IdUser == userInfo.IdUser)\
                .filter(MatchMember.Quit == False)\
                .filter(MatchMember.Refused == False).all()

    userMatchesIds = [match[0].IdMatch for match in userMatches]

    userMatchesMembers = db.session.query(MatchMember, User)\
                .join(User, MatchMember.IdUser == User.IdUser)\
                .filter(MatchMember.IdMatch.in_(userMatchesIds))\
                .filter(MatchMember.Quit != True).all()

    stores = db.session.query(Store)\
            .join(Match, Store.IdStore == Match.IdStore)\
            .filter(Match.IdMatch.in_(userMatchesIds)).distinct()

    storesIds = [store.IdStore for store in stores]

    storePhotos = db.session.query(StorePhoto).filter(StorePhoto.IdStore.in_(storesIds)).all()

    storeList = []
    for store in stores:
        storePhotoJson = []
        for storePhoto in storePhotos:
            if storePhoto.IdStore == store.IdStore:
                storePhotoJson.append(storePhoto.to_json())
        storeList.append({
            'store':store.to_json(),
            'storePhotos': storePhotoJson,
        })

    for userMatch in userMatches:
        userMatchesList.append({
                'match': userMatch[0].to_json(),
                'matchCreator': [userMatchesMember[1].FirstName for userMatchesMember in userMatchesMembers if \
                            ((userMatchesMember[0].IsMatchCreator == True) and (userMatchesMember[0].IdMatch == userMatch[0].IdMatch))][0]
            })

    notificationList = []
    notifications = db.session.query(Notification).filter(Notification.IdUser == userLogin.IdUser).all()

    for notification in notifications:
        notificationList.append(notification.to_json())

    return  jsonify({'stores': storeList, 'userMatches': userMatchesList, 'openMatchesCounter': openMatchesCounter, 'notifications': notificationList}), 200



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

    notifications = db.session.query(NotificationCategory).all()
    notificationsList = []
    for notification in notifications:
        notificationsList.append(notification.to_json())

    return  jsonify({'sports':sportsList, 'genders': gendersList, 'sidePreferences': sidePreferencesList, 'ranks': ranksList, 'notifications': notificationsList}), 200
