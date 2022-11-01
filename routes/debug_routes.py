from flask import Blueprint, jsonify, abort, request
from ..Models.feedback_model import Feedback
from ..Models.user_login_model import UserLogin
from ..Models.rank_category_model import RankCategory
from ..Models.user_rank_model import UserRank
from ..Models.user_model import User
from ..Models.store_model import Store
from ..Models.state_model import State
from ..Models.city_model import City
from ..Models.store_photo_model import StorePhoto
from ..Models.store_price_model import StorePrice
from ..Models.match_member_model import MatchMember
from ..Models.store_court_model import StoreCourt
from ..Models.store_court_sport_model import StoreCourtSport
from ..Models.match_model import Match
from ..Models.feedback_model import Feedback
from ..extensions import db
from ..Models.http_codes import HttpCode
from datetime import datetime, timedelta, date
from flask import Blueprint, jsonify, abort, request, json
from datetime import datetime, timedelta, date
from sqlalchemy import func 
from ..extensions import db
import os

from ..Models.http_codes import HttpCode
from ..Models.match_model import Match
from ..Models.user_model import User
from ..Models.user_rank_model import UserRank
from ..Models.rank_category_model import RankCategory
from ..Models.match_member_model import MatchMember
from ..Models.city_model import City
from ..Models.state_model import State
from ..Models.available_hour_model import AvailableHour
from ..Models.store_model import Store
from ..Models.store_price_model import StorePrice
from ..Models.store_photo_model import StorePhoto
from ..Models.store_court_model import StoreCourt
from ..Models.store_court_sport_model import StoreCourtSport
from ..Models.sport_model import Sport
from ..Models.user_login_model import UserLogin
from ..Models.notification_model import Notification
from ..Models.notification_category_model import NotificationCategory
from ..access_token import EncodeToken, DecodeToken

bp_debug = Blueprint('bp_debug', __name__)


def daterange(start_date, end_date):
    if start_date == end_date:
        yield start_date
    else:
        for n in range(int ((end_date - start_date).days)+1):
            yield start_date + timedelta(n)

def getHourIndex(hourString):
    return datetime.strptime(hourString, '%H:%M').hour

@bp_debug.route('/debug', methods=['GET'])
def debug():

    userLogin = UserLogin.query.filter_by(IdUser = 2).first()

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
            if (member.User.IdUser == userLogin.IdUser)  and (member.Refused == False) and (member.Quit == False):
                userAlreadyInMatch = True
                break
            else:
                if (member.WaitingApproval == False) and (member.Refused == False) and (member.Quit == False):
                    matchMemberCounter +=1
        if (userAlreadyInMatch == False) and (matchMemberCounter < openMatch.MaxUsers):
            openMatchesCounter +=1

    
    return  jsonify({'OpenMatchesCounter': openMatchesCounter}), 200
