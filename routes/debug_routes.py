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
        

        return 'a'



        #accessToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZFVzZXIiOjUsInRpbWUiOiIyMDIyLTEwLTIwIDA4OjQxOjQ1LjM3MDUzNiJ9.GD7mzvBo4bErvmMK9RCTHTQ6wAKpsIzD4IEKtKc8BaA'
        # sportId = 1
        # cityId = 4174
        # dateStart = "2022-11-30"
        # dateEnd = "2022-11-30"
        # timeStart = "08:00"
        # timeEnd = "12:00"

        # user = UserLogin.query.filter_by(AccessToken = accessToken).first()
        # if user is None:
        #         return '1', HttpCode.INVALID_ACCESS_TOKEN

        # stores = db.session.query(Store)\
        #                 .join(StoreCourt, StoreCourt.IdStore == Store.IdStore)\
        #                 .join(StoreCourtSport, StoreCourtSport.IdStoreCourt == StoreCourt.IdStoreCourt)\
        #                 .filter(StoreCourtSport.IdSport == sportId)\
        #                 .filter(Store.IdCity == cityId).all()

        # storesCourtIds = []
        # for store in stores:
        #         for court in store.Courts:
        #                 storesCourtIds.append(court.IdStoreCourt)
        # matches = db.session.query(Match)\
        #         .filter(Match.IdStoreCourt.in_(storesCourtIds))\
        #         .filter(Match.Date.in_(daterange(datetime.strptime(dateStart, '%Y-%m-%d').date(), datetime.strptime(dateEnd, '%Y-%m-%d').date())))\
        #         .filter((Match.IdTimeBegin >= getHourIndex(timeStart)) & (Match.IdTimeBegin <= getHourIndex(timeEnd)))\
        #         .filter(Match.Canceled == False).all()

        # jsonOpenMatches = []
        
        # for validDate in daterange(datetime.strptime(dateStart, '%Y-%m-%d').date(), datetime.strptime(dateEnd, '%Y-%m-%d').date()):
        #         print("SS")
        #         i = 0
        #         for store in stores:                        
        #                 #descobre horario que o estabelecimento abre e fecha
        #                 firstHour = 24
        #                 lastHour = 0
        #                 for storePrice in store.Courts[0].Prices:
        #                         if(storePrice.Weekday == validDate.weekday()):
        #                                 if storePrice.IdAvailableHour < firstHour:
        #                                         firstHour = storePrice.IdAvailableHour
        #                                 if storePrice.IdAvailableHour > lastHour:
        #                                         lastHour = storePrice.IdAvailableHour
        #                 if firstHour < getHourIndex(timeStart):
        #                         firstHour = getHourIndex(timeStart)
        #                 if lastHour > getHourIndex(timeEnd):
        #                         lastHour = getHourIndex(timeEnd)
                        
        #                 for hour in range(firstHour, lastHour + 1):
        #                         for court in store.Courts:
        #                                 hasConcurrentMatch = False
        #                                 for match in matches:
        #                                         if (match.IdStoreCourt == court.IdStoreCourt) and\ 
        #                                                 (match.Canceled == False) and\
        #                                                 ((match.IdTimeBegin == storeOperationHour.IdAvailableHour) or ((match.IdTimeBegin < storeOperationHour.IdAvailableHour) and (match.IdTimeEnd > storeOperationHour.IdAvailableHour)))\


    
