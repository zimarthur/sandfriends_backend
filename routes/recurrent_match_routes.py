from flask import Blueprint, jsonify, abort, request
from ..extensions import db
from ..utils import getLastDayOfMonth
from datetime import datetime, timedelta, date
from ..utils import getFirstDayOfLastMonth
from ..responses import webResponse

from ..Models.recurrent_match_model import RecurrentMatch
from ..Models.http_codes import HttpCode
from ..Models.match_model import Match
from ..Models.user_model import User
from ..Models.employee_model import Employee
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
from ..Models.user_model import User



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


@bp_recurrent_match.route('/AvailableRecurrentMatches', methods=['POST'])
def AvailableRecurrentMatches():
    if not request.json:
        
        abort(400)

    weekday = request.json.get('AccessToken')
    return "a", 200

@bp_recurrent_match.route('/UserRecurrentMatches', methods=['POST'])
def UserRecurrentMatches():
    
    accessToken = request.json.get('AccessToken')

    user = User.query.filter_by(AccessToken = accessToken).first()

    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN

    
    recurrentMatches = db.session.query(RecurrentMatch)\
                        .filter(RecurrentMatch.IdUser == user.IdUser)\
                        .filter(RecurrentMatch.Canceled == False)\
                        .filter( ((RecurrentMatch.LastPaymentDate == RecurrentMatch.CreationDate) & (datetime.today().replace(day=1).date() <= RecurrentMatch.CreationDate)) | \
                        ((RecurrentMatch.LastPaymentDate != RecurrentMatch.CreationDate) & (RecurrentMatch.LastPaymentDate >= getFirstDayOfLastMonth()))).all()

    if recurrentMatches is None:
        return "nada", 200
    
    recurrentMatchesList =[]
    for recurrentMatch in recurrentMatches:
        recurrentMatchesList.append(recurrentMatch.to_json())
    
    return jsonify({'RecurrentMatches': recurrentMatchesList}), HttpCode.SUCCESS



@bp_recurrent_match.route("/SearchRecurrentCourts", methods=["POST"])
def SearchRecurrentCourts():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessToken = request.json.get('AccessToken')
    sportId = int(request.json.get('IdSport'))
    cityId = request.json.get('IdCity')
    days = request.json.get('Days').split(";")
    timeStart = request.json.get('TimeStart')
    timeEnd = request.json.get('TimeEnd')

    user = User.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN

    stores = db.session.query(Store).filter(Store.IdCity == cityId)\
                                    .filter(Store.IsApproved).all()

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
                        ((RecurrentMatch.LastPaymentDate != RecurrentMatch.CreationDate) & (RecurrentMatch.LastPaymentDate >= getFirstDayOfLastMonth()))).all()

    dayList = []
    IdStoresList = []
    a = []
    b = []
    for day in days:
        jsonStores = []
        for store in stores:
            b = []
            filteredCourts = [court for court in courts if court.IdStore == store.IdStore]
            for la in filteredCourts:
                b.append({
                    "id":la.IdStoreCourt
                    })
            a.append({
                "day": day,
                "store": store.IdStore,
                "idCourt":b,
            })
    #return jsonify({"a":a}), 200
            if(len(filteredCourts) > 0):
                storeOperationHours = [storeOperationHour for storeOperationHour in courtHours if \
                                    (storeOperationHour.IdStoreCourt == filteredCourts[0].IdStoreCourt) and\
                                    (storeOperationHour.Weekday == int(day)) and \
                                    ((storeOperationHour.IdAvailableHour >= getHourIndex(timeStart)) and (storeOperationHour.IdAvailableHour < getHourIndex(timeEnd)))]

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
                        'Hours':jsonStoreOperationHours
                    })
                    if store.IdStore not in IdStoresList:
                        IdStoresList.append(store.IdStore)

        if jsonStores:
            dayList.append({
                'Date':day, 
                'Stores':jsonStores
                })

    

    return jsonify({'Dates':dayList, 'Stores':[store.to_json() for store in stores]})

   

@bp_recurrent_match.route("/RecurrentMatchReservation", methods=["POST"])
def CourtReservation():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idStoreCourt = request.json.get('IdStoreCourt')
    sportId = request.json.get('SportId')
    weekDay = int(request.json.get('Weekday'))
    timeStart = int(request.json.get('TimeBegin'))
    timeEnd = int(request.json.get('TimeEnd'))
    cost = request.json.get('Cost')

    user = User.query.filter_by(AccessToken = accessToken).first()

    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN

    #verifica se alguma partida mensalista ou algum bloqueio foi feite nesse horario
    recurrentMatch = db.session.query(RecurrentMatch)\
                        .filter(RecurrentMatch.IdStoreCourt == int(idStoreCourt)) \
                        .filter(RecurrentMatch.Weekday == weekDay) \
                        .filter(RecurrentMatch.Canceled == False)\
                        .filter(((Match.IdTimeBegin >= timeStart) & (Match.IdTimeBegin < timeEnd))  | \
                        ((Match.IdTimeEnd > timeStart) & (Match.IdTimeEnd <= timeEnd))      | \
                        ((Match.IdTimeBegin < timeStart) & (Match.IdTimeEnd > timeStart))   \
                        ).first()
    if recurrentMatch is not None:
        return "Ops, esse horário não está mais disponível", HttpCode.WARNING

    daysList = [day for day in daterange(datetime.today().date(), getLastDayOfMonth(datetime.now())) if day.weekday() == weekDay]
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
        IdSport = sportId,
        IdTimeBegin = timeStart,
        IdTimeEnd = timeEnd,
        LastPaymentDate = creationDate,
    )
    db.session.add(newRecurrentMatch)
    db.session.commit()
    myList=[]
    for day in daysList:
        concurrentMatch = [match for match in matches if match.Date == day]
        if not concurrentMatch:
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
            
    return "Seus horários mensalistas foram agendados!", HttpCode.ALERT
   


@bp_recurrent_match.route("/CancelRecurrentMatchEmployee", methods=["POST"])
def CancelRecurrentMatchEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    idRecurrentMatchReq = request.json.get('IdRecurrentMatch')
    cancelationReasonReq = request.json.get('CancelationReason')

    #busca a loja a partir do token do employee
    storeCourt = db.session.query(StoreCourt).\
            join(Employee, Employee.IdStore == StoreCourt.IdStore)\
            .filter(Employee.AccessToken == accessTokenReq).first()
    
    #Caso não encontrar Token
    if storeCourt is None:
        return webResponse("Token não encontrado", None), HttpCode.WARNING

    recurrentMatch = RecurrentMatch.query.get(idRecurrentMatchReq)
    if recurrentMatch is None:
        return 'Mensalista não encontrada', HttpCode.WARNING
    else:
        
        recurrentMatch.Canceled = True
        recurrentMatch.BlockedReason = cancelationReasonReq
        
        db.session.commit()

        courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == storeCourt.IdStore).all()

        recurrentMatches = db.session.query(RecurrentMatch).filter(RecurrentMatch.IdStoreCourt.in_([court.IdStoreCourt for court in courts]))\
                            .filter(RecurrentMatch.Canceled == False)\
                            .filter(RecurrentMatch.IsExpired == False).all()
    
        recurrentMatchList =[]
        for recurrentMatch in recurrentMatches:
            recurrentMatchList.append(recurrentMatch.to_json_store())

        return jsonify({"RecurrentMatches": recurrentMatchList}), HttpCode.SUCCESS


@bp_recurrent_match.route('/RecurrentBlockUnblockHour', methods=['POST'])
def RecurrentBlockUnblockHour():
    if not request.json:
        abort(400)

    accessTokenReq = request.json.get('AccessToken')
    idStoreCourtReq = request.json.get('IdStoreCourt')

    #busca a loja a partir do token do employee
    storeCourt = db.session.query(StoreCourt).\
            join(Employee, Employee.IdStore == StoreCourt.IdStore)\
            .filter(Employee.AccessToken == accessTokenReq)\
            .filter(StoreCourt.IdStoreCourt == idStoreCourtReq).first()
    
    #Caso não encontrar Token
    if storeCourt is None:
        return webResponse("Token não encontrado", None), HttpCode.WARNING

    idHourReq = request.json.get('IdHour')
    weekdayReq = request.json.get('Weekday')

    recurrentMatch = db.session.query(RecurrentMatch)\
                .filter(RecurrentMatch.Weekday == weekdayReq)\
                .filter((RecurrentMatch.IdTimeBegin == idHourReq) | ((RecurrentMatch.IdTimeBegin < idHourReq) & (RecurrentMatch.IdTimeEnd > idHourReq)))\
                .filter(RecurrentMatch.IdStoreCourt == idStoreCourtReq).first()


    blockedReq = request.json.get('Blocked')
    blockedReasonReq = request.json.get('BlockedReason')
    idSportReq = request.json.get('IdSport')

    if recurrentMatch is None:
        newRecurrentMatch = RecurrentMatch(
            IdStoreCourt = idStoreCourtReq,
            IdSport = idSportReq,
            IdUser = None,
            Weekday = weekdayReq,
            IdTimeBegin = idHourReq,
            IdTimeEnd = idHourReq+1,
            CreationDate = datetime.now(),
            LastPaymentDate = datetime.now(),
            Canceled = False,
            Blocked = blockedReq,
            BlockedReason = blockedReasonReq,
        )
        db.session.add(newRecurrentMatch)

    else:
        #alguem marcou mensalista nesse meio tempo
        if recurrentMatch.IsExpired == False and recurrentMatch.Canceled == False:
            return webResponse("Ops", "Não foi possível bloquear o horário. Um mensalista já foi marcado nesse horário"), HttpCode.WARNING
        
        #em teoria se chegou aqui é para desbloquear um horário, coloquei esse if só pra ter certeza
        if blockedReq == False:
            db.session.delete(recurrentMatch)
        else:
            recurrentMatch.Canceled = False
            recurrentMatch.Blocked = blockedReq
            recurrentMatch.BlockedReason = blockedReasonReq
    
    db.session.commit()

    courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == storeCourt.IdStore).all()

    recurrentMatches = db.session.query(RecurrentMatch).filter(RecurrentMatch.IdStoreCourt.in_([court.IdStoreCourt for court in courts]))\
                        .filter(RecurrentMatch.Canceled == False)\
                        .filter(RecurrentMatch.IsExpired == False).all()

    recurrentMatchList =[]
    for recurrentMatch in recurrentMatches:
        recurrentMatchList.append(recurrentMatch.to_json_store())

    return jsonify({"RecurrentMatches": recurrentMatchList}), HttpCode.SUCCESS
