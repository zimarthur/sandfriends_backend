from flask import Blueprint, jsonify, abort, request
from ..extensions import db
from ..utils import getLastDayOfMonth
from datetime import datetime, timedelta, date
from ..utils import getFirstDayOfLastMonth
from ..responses import webResponse
from ..routes.store_routes import getAvailableStores
from ..Models.recurrent_match_model import RecurrentMatch
from ..Models.http_codes import HttpCode
from ..Models.match_model import Match
from ..Models.user_model import User
from ..Models.user_credit_card_model import UserCreditCard
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

from ..Asaas.Customer.update_customer import updateCpf
from ..Asaas.Payment.create_payment import createPaymentPix, createPaymentCreditCard
from ..Asaas.Payment.generate_qr_code import generateQrCode

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


@bp_recurrent_match.route('/UserRecurrentMatches', methods=['POST'])
def UserRecurrentMatches():
    
    accessToken = request.json.get('AccessToken')

    user = User.query.filter_by(AccessToken = accessToken).first()

    if user is None:
        return '1', HttpCode.EXPIRED_TOKEN

    
    recurrentMatches = db.session.query(RecurrentMatch)\
                        .filter(RecurrentMatch.IdUser == user.IdUser)\
                        .filter(RecurrentMatch.Canceled == False)\
                        .filter( RecurrentMatch.ValidUntil > datetime.now()).all()

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
        return '1', HttpCode.EXPIRED_TOKEN

    stores = db.session.query(Store).filter(Store.IdCity == cityId)\
                                    .filter(Store.IdStore.in_([store.IdStore for store in getAvailableStores()])).all()

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
                        .filter(RecurrentMatch.ValidUntil > datetime.now()).all()

    recurrentMatches = [recurrentMatch for recurrentMatch in recurrentMatches if recurrentMatch.isPaymentExpired == False]

    dayList = []
    IdStoresList = []
    for day in days:
        jsonStores = []
        for store in stores:
            filteredCourts = [court for court in courts if court.IdStore == store.IdStore]
            
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
                        if len(concurrentMatch) == 0:
                            jsonAvailableCourts.append({
                                'IdStoreCourt':filteredCourt.IdStoreCourt,
                                'Price': [int(courtHour.RecurrentPrice) for courtHour in courtHours if (courtHour.IdStoreCourt == filteredCourt.IdStoreCourt) and (courtHour.Weekday == int(day)) and (courtHour.IdAvailableHour == storeOperationHour.IdAvailableHour)][0]
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

    accessTokenReq = request.json.get('AccessToken')
    idStoreCourtReq = request.json.get('IdStoreCourt')
    sportIdReq = request.json.get('SportId')
    weekDayReq = int(request.json.get('Weekday'))
    timeStartReq = int(request.json.get('TimeBegin'))
    timeEndReq = int(request.json.get('TimeEnd'))
    costReq = request.json.get('Cost')
    totalCostReq = request.json.get('TotalCost')
    currentMonthDatesReq = request.json.get('CurrentMonthDates')
    paymentReq = request.json.get('Payment')
    cpfReq = request.json.get('Cpf')
    isRenovatingReq = request.json.get('IsRenovating')

    if request.json.get("IdCreditCard")== "": 
        idCreditCardReq =  None 
    else: 
        idCreditCardReq = request.json.get("IdCreditCard")
    

    user = User.query.filter_by(AccessToken = accessTokenReq).first()

    if user is None:
        return '1', HttpCode.EXPIRED_TOKEN

    #verifica se alguma partida mensalista ou algum bloqueio foi feite nesse horario
    recurrentMatches = db.session.query(RecurrentMatch)\
                        .filter(RecurrentMatch.IdStoreCourt == int(idStoreCourtReq)) \
                        .filter(RecurrentMatch.Weekday == weekDayReq) \
                        .filter(RecurrentMatch.Canceled == False)\
                        .filter(((RecurrentMatch.IdTimeBegin >= timeStartReq) & (RecurrentMatch.IdTimeBegin < timeEndReq))  | \
                        ((RecurrentMatch.IdTimeEnd > timeStartReq) & (RecurrentMatch.IdTimeEnd <= timeEndReq))      | \
                        ((RecurrentMatch.IdTimeBegin < timeStartReq) & (RecurrentMatch.IdTimeEnd > timeStartReq))   \
                        ).all()
    
    recurrentMatches = [recurrentMatch for recurrentMatch in recurrentMatches if recurrentMatch.isPaymentExpired == False]

    if (len(recurrentMatches) > 0) and (isRenovatingReq == False):
        return "Ops, esse horário não está mais disponível", HttpCode.WARNING

    daysList = [datetime.strptime(day, '%d/%m/%Y') for day in currentMonthDatesReq]
    concurrentMatches = Match.query.filter((Match.IdStoreCourt == int(idStoreCourtReq)) \
                & (Match.Date.in_(daysList)) \
                & (((Match.IdTimeBegin >= timeStartReq) & (Match.IdTimeBegin < timeEndReq))  | \
                ((Match.IdTimeEnd > timeStartReq) & (Match.IdTimeEnd <= timeEndReq))      | \
                ((Match.IdTimeBegin < timeStartReq) & (Match.IdTimeEnd > timeStartReq))   \
                )).all()

    if len(concurrentMatches) > 0 :
        return "Ops, um dos horários não está mais disponível. Pesquise novamente", HttpCode.WARNING
    
    asaasPaymentId = None
    asaasBillingType = None
    asaasPaymentStatus = None
    asaasPixCode = None

    #PIX
    if paymentReq == 1:
        if cpfReq != user.Cpf:
            user.Cpf = cpfReq
            db.session.commit()
            responseCpf = updateCpf(user)

            if responseCpf.status_code != 200:
                return "Não foi possível criar suas partida. Tente novamente", HttpCode.WARNING

        responsePayment = createPaymentPix(user, totalCostReq)
        if responsePayment.status_code != 200:
            return "Não foi possível processar seu pagamento. Tente novamente", HttpCode.WARNING

        responsePixCode = generateQrCode(responsePayment.json().get('id'))

        asaasPaymentId = responsePayment.json().get('id')
        asaasBillingType = responsePayment.json().get('billingType')
        asaasPaymentStatus = responsePayment.json().get('status')
        
        if responsePixCode.status_code == 200:
            asaasPixCode = responsePixCode.json().get('payload')

    elif paymentReq == 2:
        creditCard = db.session.query(UserCreditCard).filter(UserCreditCard.IdUserCreditCard == idCreditCardReq).first()

        if creditCard is None:
            return "Não foi possível processar seu pagamento. Tente novamente", HttpCode.WARNING
        
        responsePayment = createPaymentCreditCard(
            user= user, 
            creditCard= creditCard,
            value= totalCostReq,
        )
        
        if responsePayment.status_code != 200:
            return "Não foi possível processar seu pagamento. Tente novamente", HttpCode.WARNING

        asaasPaymentId = responsePayment.json().get('id'),
        asaasBillingType = responsePayment.json().get('billingType'),
        asaasPaymentStatus = responsePayment.json().get('status'),

    else:
        return "Forma de pagamento inválida", HttpCode.WARNING


    now = datetime.now()

    recurrentMatchId = None
    if isRenovatingReq:
        recurrentMatch = db.session.query(RecurrentMatch)\
            .filter(RecurrentMatch.IdStoreCourt == int(idStoreCourtReq)) \
            .filter(RecurrentMatch.Weekday == weekDayReq) \
            .filter(RecurrentMatch.Canceled == False)\
            .filter((RecurrentMatch.IdTimeBegin == timeStartReq) & (RecurrentMatch.IdTimeEnd == timeEndReq)).first()
       
        recurrentMatch.LastPaymentDate = now.date()
        recurrentMatch.ValidUntil = getLastDayOfMonth(datetime(now.year, now.month+1, 1))
        recurrentMatchId = recurrentMatch.IdRecurrentMatch
        db.session.commit()
    else:
        newRecurrentMatch = RecurrentMatch(
            IdUser = user.IdUser,
            IdStoreCourt = idStoreCourtReq,
            CreationDate = now,
            Canceled = False,
            Weekday = weekDayReq,
            IdSport = sportIdReq,
            IdTimeBegin = timeStartReq,
            IdTimeEnd = timeEndReq,
            LastPaymentDate = now.date(),
            ValidUntil = getLastDayOfMonth(now)
        )
        db.session.add(newRecurrentMatch)
        db.session.commit()
        db.session.refresh(newRecurrentMatch)
        recurrentMatchId = newRecurrentMatch.IdRecurrentMatch
    

    for day in daysList:
        newMatch = Match(
            IdStoreCourt = idStoreCourtReq,
            IdSport = sportIdReq,
            Date = day,
            IdTimeBegin = timeStartReq,
            IdTimeEnd = timeEndReq,
            Cost = costReq,
            OpenUsers = False,
            MaxUsers = 0,
            Canceled = False,
            CreationDate = now,
            CreatorNotes = "",
            IdRecurrentMatch = recurrentMatchId,
            AsaasPaymentId = asaasPaymentId,
            AsaasBillingType = asaasBillingType,
            AsaasPaymentStatus = asaasPaymentStatus,
            AsaasPixCode = asaasPixCode,
            IdUserCreditCard = idCreditCardReq,
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


@bp_recurrent_match.route("/RecurrentMonthAvailableHours", methods=["POST"])
def RecurrentMonthAvailableHours():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idStoreCourt = request.json.get('IdStoreCourt')
    weekDay = int(request.json.get('Weekday'))
    timeStart = int(request.json.get('TimeBegin'))
    timeEnd = int(request.json.get('TimeEnd'))
    isRenovating = request.json.get('IsRenovating')

    user = User.query.filter_by(AccessToken = accessToken).first()

    if user is None:
        return '1', HttpCode.EXPIRED_TOKEN

    #verifica se alguma partida mensalista ou algum bloqueio foi feite nesse horario
    recurrentMatch = db.session.query(RecurrentMatch)\
                        .filter(RecurrentMatch.IdStoreCourt == int(idStoreCourt)) \
                        .filter(RecurrentMatch.Weekday == weekDay) \
                        .filter(RecurrentMatch.Canceled == False)\
                        .filter(((RecurrentMatch.IdTimeBegin >= timeStart) & (RecurrentMatch.IdTimeBegin < timeEnd))  | \
                        ((RecurrentMatch.IdTimeEnd > timeStart) & (RecurrentMatch.IdTimeEnd <= timeEnd))      | \
                        ((RecurrentMatch.IdTimeBegin < timeStart) & (RecurrentMatch.IdTimeEnd > timeStart))   \
                        ).first()
    
    if (recurrentMatch is not None) and (isRenovating == False):
        return "Ops, esse horário não está mais disponível", HttpCode.WARNING

    if isRenovating:
        nextMonth = datetime(datetime.today().year, datetime.today().month + 1, 1)
        daysList = [day for day in daterange( nextMonth.date(), getLastDayOfMonth(nextMonth)) if day.weekday() == weekDay]
    else:
        daysList = [day for day in daterange(datetime.today().date(), getLastDayOfMonth(datetime.now())) if day.weekday() == weekDay]
    matches = Match.query.filter((Match.IdStoreCourt == int(idStoreCourt)) \
                & (Match.Date.in_(daysList)) \
                & (((Match.IdTimeBegin >= timeStart) & (Match.IdTimeBegin < timeEnd))  | \
                ((Match.IdTimeEnd > timeStart) & (Match.IdTimeEnd <= timeEnd))      | \
                ((Match.IdTimeBegin < timeStart) & (Match.IdTimeEnd > timeStart))   \
                )).all()

    recurrentMonthAvailableHours = []

    for day in daysList:
        concurrentMatch = [match for match in matches if match.Date == day]
        if not concurrentMatch:
            recurrentMonthAvailableHours.append(day.strftime("%d/%m/%Y"))
            
    return jsonify({"RecurrentMonthAvailableHours": recurrentMonthAvailableHours}), HttpCode.SUCCESS
   


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
