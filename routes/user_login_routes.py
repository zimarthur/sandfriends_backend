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



def IsNewUser(UserLogin):
    if UserLogin.User == None:
        return True
    else:
        return False


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
        return userLogin.to_json(), HttpCode.SUCCESS
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

@bp_user_login.route("/LogIn", methods=["POST"])
def LogIn():
    if not request.json:
        abort(HttpCode.ABORT)
    
    email = request.json.get('Email')
    password = request.json.get('Password')
    thirdPartyLogin = request.json.get('ThirdPartyLogin')

    userLogin = UserLogin.query.filter_by(Email=email).first()

    if thirdPartyLogin:
        if not userLogin: #sign up with new google account
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

    openMatches = db.session.query(Match)\
                .join(StoreCourt, StoreCourt.IdStoreCourt == Match.IdStoreCourt)\
                .join(Store, Store.IdStore == StoreCourt.IdStore)\
                .filter(Match.OpenUsers == True)\
                .filter((Match.Date > datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.IdTimeBegin >= int(datetime.now().strftime("%H")))))\
                .filter(Match.Canceled == False)\
                .filter(Match.IdSport == userLogin.User.IdSport)\
                .filter(Store.IdCity == userLogin.User.IdCity).all()
    
    openMatchesCounter = 0

    for openMatch in openMatches:
        userAlreadyInMatch = False
        matchMemberCounter = 0
        for member in openMatch.Members:
            if (member.User.IdUser == userLogin.IdUser) and (member.Quit == False) and (member.WaitingApproval == False):
                userAlreadyInMatch = True
                break
            else:
                if (member.WaitingApproval == False) and (member.Refused == False) and (member.Quit == False):
                    matchMemberCounter +=1
        if (userAlreadyInMatch == False) and (matchMemberCounter < openMatch.MaxUsers):
            openMatchesCounter +=1

    userMatchesList = []

    userMatches =  db.session.query(Match)\
                .join(MatchMember, Match.IdMatch == MatchMember.IdMatch)\
                .filter(MatchMember.IdUser == userLogin.IdUser)\
                .filter(MatchMember.Quit == False)\
                .filter(MatchMember.Refused == False).all()

    for userMatch in userMatches:
        for member in userMatch.Members:
            if member.IsMatchCreator == True:
                matchCreator = member
                break
        userMatchesList.append(userMatch.to_json())



    notificationList = []
    notifications = db.session.query(Notification).filter(Notification.IdUser == userLogin.IdUser).all()
    
    for notification in notifications:
        notificationList.append(notification.to_json())
        notification.Seen = True
        db.session.commit()

    return  jsonify({'UserMatches': userMatchesList, 'OpenMatchesCounter': openMatchesCounter, 'Notifications': notificationList}), 200




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
