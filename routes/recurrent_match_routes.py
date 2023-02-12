from flask import Blueprint, jsonify, abort, request
from ..extensions import db
from datetime import datetime, timedelta, date

from ..Models.recurrent_match_model import RecurrentMatch
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



bp_recurrent_match = Blueprint('bp_recurrent_match', __name__)

def daterange(start_date, end_date):
    if start_date == end_date:
        yield start_date
    else:
        for n in range(int ((end_date - start_date).days)+1):
            yield start_date + timedelta(n)

def getHourIndex(hourString):
    return datetime.strptime(hourString, '%H:%M').hour

def getHourString(hourIndex):
    print(hourIndex)
    print(type(hourIndex))
    print(f"{hourIndex}:00")
    return f"{hourIndex}:00"#GAMBIARRA

def getLastMonth():
    return (datetime.today().replace(day=1) - timedelta(days=1)).replace(day=1).date()

def getLastDayOfMonth():
    next_month = datetime.today().replace(day=28) + timedelta(days=4)
    res = next_month - timedelta(days=next_month.day)
    return res.date()

@bp_recurrent_match.route('/AvailableRecurrentMatches', methods=['POST'])
def AvailableRecurrentMatches():
    if not request.json:
        
        abort(400)

    weekday = request.json.get('AccessToken')
    return "a", 200

@bp_recurrent_match.route('/UserRecurrentMatches', methods=['POST'])
def UserRecurrentMatches():
    
    accessToken = request.json.get('AccessToken')

    user = UserLogin.query.filter_by(AccessToken = accessToken).first()

    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN

    
    recurrentMatches = db.session.query(RecurrentMatch)\
                        .filter(RecurrentMatch.IdUser == user.IdUser)\
                        .filter(RecurrentMatch.Canceled == False)\
                        .filter( ((RecurrentMatch.LastPaymentDate == RecurrentMatch.CreationDate) & (datetime.today().replace(day=1).date() <= RecurrentMatch.CreationDate)) | \
                        ((RecurrentMatch.LastPaymentDate != RecurrentMatch.CreationDate) & (RecurrentMatch.LastPaymentDate >= getLastMonth()))).all()

    if recurrentMatches is None:
        return "nada", 200
    
    recurrentMatchesList =[]
    for recurrentMatch in recurrentMatches:
        recurrentMatchesList.append(recurrentMatch.to_json())
    
    return jsonify({'RecurrentMatches': recurrentMatchesList}), HttpCode.SUCCESS



@bp_recurrent_match.route("/SearchRecurrentMatches", methods=["POST"])
def SearchCourts():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessToken = request.json.get('accessToken')
    sportId = int(request.json.get('sportId'))
    cityId = request.json.get('cityId')
    days = request.json.get('days').split(";")
    timeStart = request.json.get('timeStart')
    timeEnd = request.json.get('timeEnd')

    user = UserLogin.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN

    stores = db.session.query(Store).filter(Store.IdCity == cityId).all()

    courts = db.session.query(StoreCourt)\
                    .join(StoreCourtSport, StoreCourtSport.IdStoreCourt == StoreCourt.IdStoreCourt)\
                    .join(Store, Store.IdStore == StoreCourt.IdStore)\
                    .filter(Store.IdCity == cityId)\
                    .filter(StoreCourtSport.IdSport == sportId)\
                    .filter(StoreCourt.IdStore.in_(store.IdStore for store in stores)).all()

    courtHours = db.session.query(StorePrice)\
                    .filter(StorePrice.IdStoreCourt.in_(court.IdStoreCourt for court in courts)).all()
    
    recurrentMatches = db.session.query(RecurrentMatch)\
                        .filter(RecurrentMatch.Canceled == False)\
                        .filter(RecurrentMatch.IdStoreCourt.in_(court.IdStoreCourt for court in courts))\
                        .filter( ((RecurrentMatch.LastPaymentDate == RecurrentMatch.CreationDate) & (datetime.today().replace(day=1).date() <= RecurrentMatch.CreationDate)) | \
                        ((RecurrentMatch.LastPaymentDate != RecurrentMatch.CreationDate) & (RecurrentMatch.LastPaymentDate >= getLastMonth()))).all()

    dayList = []
    IdStoresList = []
    IdStoreCourtList = []
    for day in days:
        jsonStores = []
        for store in stores:
            filteredCourts = [court for court in courts if court.IdStore == store.IdStore]

            storeOperationHours = [storeOperationHour for storeOperationHour in courtHours if \
                                (storeOperationHour.IdStoreCourt == filteredCourts[0].IdStoreCourt) and\
                                (storeOperationHour.Weekday == int(day)) and \
                                ((storeOperationHour.IdAvailableHour >= getHourIndex(timeStart)) and (storeOperationHour.IdAvailableHour <= getHourIndex(timeEnd)))]

            jsonStoreOperationHours =[]
            for storeOperationHour in storeOperationHours:
                jsonAvailableCourts =[]
                for filteredCourt in filteredCourts:
                    concurrentMatch = [match for match in recurrentMatches if \
                                (match.IdStoreCourt ==  filteredCourt.IdStoreCourt) and \
                                (match.Canceled == False) and \
                                ((match.IdTimeBegin == storeOperationHour.IdAvailableHour) or ((match.IdTimeBegin < storeOperationHour.IdAvailableHour) and (match.IdTimeEnd > storeOperationHour.IdAvailableHour)))\
                                ]
                    if not concurrentMatch:
                        jsonAvailableCourts.append({
                            'IdStoreCourt':filteredCourt.IdStoreCourt,
                            'Price': [int(courtHour.Price) for courtHour in courtHours if (courtHour.IdStoreCourt == filteredCourt.IdStoreCourt) and (courtHour.Weekday == int(day)) and (courtHour.IdAvailableHour == storeOperationHour.IdAvailableHour)][0]
                        })
                        if filteredCourt.IdStoreCourt not in IdStoreCourtList:
                            IdStoreCourtList.append(filteredCourt.IdStoreCourt)

                if jsonAvailableCourts:
                    jsonStoreOperationHours.append({
                        'Courts': jsonAvailableCourts, 
                        'TimeBegin':storeOperationHour.AvailableHour.HourString,
                        'TimeFinish':getHourString(storeOperationHour.IdAvailableHour + 1),
                        'TimeInteger': storeOperationHour.IdAvailableHour
                    })
            if jsonStoreOperationHours:
                jsonStores.append({
                    'IdStore':store.IdStore, 
                    'Available':jsonStoreOperationHours
                })
                if store.IdStore not in IdStoresList:
                    IdStoresList.append(store.IdStore)

        if jsonStores:
            dayList.append({
                'Date':day, 
                'Places':jsonStores
                })

    jsonStoreList = []
    for store in stores:
        jsonStoreList.append({
            'Store':store.to_json(),
        })

    if dayList or jsonOpenMatches:
        return jsonify({'Dates':dayList, 'Stores':jsonStoreList, 'Courts':[court.to_json() for court in courts if court.IdStoreCourt in IdStoreCourtList]})
    else:
        return "No Result", HttpCode.NO_SEARCH_RESULTS
   

@bp_recurrent_match.route("/RecurrentMatchReservation", methods=["POST"])
def CourtReservation():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('accessToken')
    idStoreCourt = request.json.get('idStoreCourt')
    sportId = request.json.get('sportId')
    weekDay = int(request.json.get('weekDay'))
    timeStart = getHourIndex(request.json.get('timeStart'))
    timeEnd = getHourIndex(request.json.get('timeEnd'))
    cost = request.json.get('cost')

    user = UserLogin.query.filter_by(AccessToken = accessToken).first()

    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN

    daysList = [day for day in daterange(datetime.today().date(), getLastDayOfMonth()) if day.weekday() == weekDay]
    matches = Match.query.filter((Match.IdStoreCourt == int(idStoreCourt)) \
                & (Match.Date.in_(daysList)) \
                & (((Match.IdTimeBegin >= timeStart) & (Match.IdTimeBegin < timeEnd))  | \
                ((Match.IdTimeEnd > timeStart) & (Match.IdTimeEnd <= timeEnd))      | \
                ((Match.IdTimeBegin < timeStart) & (Match.IdTimeEnd > timeStart))   \
                )).all()

    creationDate = datetime.now().date()
    newRecurrentMatch = RecurrentMatch(
        IdUser = user.IdUser,
        IdStoreCourt = idStoreCourt,
        CreationDate = creationDate,
        Canceled = False,
        Weekday = weekDay,
        IdTimeBegin = timeStart,
        IdTimeEnd = timeEnd,
        LastPaymentDate = creationDate,
    )
    db.session.add(newRecurrentMatch)
    db.session.commit()
    myList=[]
    for day in daysList:
        print("day")
        print(day)
        concurrentMatch = [match for match in matches if match.Date == day]
        print("concurrentMatch")
        print(concurrentMatch)
        for a in concurrentMatch:
            myList.append(a.to_json())
        if not concurrentMatch:
            print("ENTROU")
            newMatch = Match(
                IdStoreCourt = idStoreCourt,
                IdSport = sportId,
                Date = day,
                IdTimeBegin = timeStart,
                IdTimeEnd = timeEnd,
                Cost = cost,
                OpenUsers = False,
                MaxUsers = 0,
                Canceled = False,
                CreationDate = datetime.now(),
                CreatorNotes = "",
                IdRecurrentMatch = newRecurrentMatch.IdRecurrentMatch,
            )
            db.session.add(newMatch)
            db.session.commit()
            newMatch.MatchUrl = f'{newMatch.IdMatch}{int(round(newMatch.CreationDate.timestamp()))}'
            db.session.commit()
            matchMember = MatchMember(
                IdUser = user.IdUser,
                IsMatchCreator = True,
                WaitingApproval = False,
                Refused = False,
                IdMatch = newMatch.IdMatch,
                Quit = False,
                EntryDate = datetime.now(),
            )
            db.session.add(matchMember)
            db.session.commit()
            
    return jsonify({'Dates':myList})
    # matches = Match.query.filter((Match.IdStoreCourt == int(idStoreCourt)) & (Match.Date == date) & (\
    #             ((Match.IdTimeBegin >= timeBegin) & (Match.IdTimeBegin < timeEnd))  | \
    #             ((Match.IdTimeEnd > timeBegin) & (Match.IdTimeEnd <= timeEnd))      | \
    #             ((Match.IdTimeBegin < timeBegin) & (Match.IdTimeEnd > timeBegin))   \
    #             )).first()
    # if not(matches is None):
    #     return "TIME_NO_LONGER_AVAILABLE", HttpCode.TIME_NO_LONGER_AVAILABLE
    # else:
    #     user = UserLogin.query.filter_by(AccessToken = accessToken).first()

    #     if user is None:
    #         return '1', HttpCode.INVALID_ACCESS_TOKEN
    #     newMatch = Match(
    #         IdStoreCourt = idStoreCourt,
    #         IdSport = sportId,
    #         Date = date,
    #         IdTimeBegin = timeBegin,
    #         IdTimeEnd = timeEnd,
    #         Cost = cost,
    #         OpenUsers = False,
    #         MaxUsers = 0,
    #         Canceled = False,
    #         CreationDate = datetime.now(),
    #         CreatorNotes = "",
    #         IdRecurrentMatch = 0,
    #     )
    #     db.session.add(newMatch)
    #     db.session.commit()
    #     newMatch.MatchUrl = f'{newMatch.IdMatch}{int(round(newMatch.CreationDate.timestamp()))}'
    #     db.session.commit()
    #     matchMember = MatchMember(
    #         IdUser = user.IdUser,
    #         IsMatchCreator = True,
    #         WaitingApproval = False,
    #         Refused = False,
    #         IdMatch = newMatch.IdMatch,
    #         Quit = False,
    #         EntryDate = datetime.now(),
    #     )
    #     db.session.add(matchMember)
    #     db.session.commit()
    #     return str(newMatch.IdMatch), 200
