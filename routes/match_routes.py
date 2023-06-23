from flask import Blueprint, jsonify, abort, request, json
from datetime import datetime, timedelta, date
from sqlalchemy import func 
from ..extensions import db
import os
from ..responses import webResponse
from ..utils import firstSundayOnNextMonth, lastSundayOnLastMonth, isCurrentMonth
from ..Models.http_codes import HttpCode
from ..Models.match_model import Match
from ..Models.recurrent_match_model import RecurrentMatch
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
from ..Models.employee_model import Employee
from ..Models.store_court_sport_model import StoreCourtSport
from ..Models.sport_model import Sport
from ..Models.user_model import User
from ..Models.notification_model import Notification
from ..Models.notification_category_model import NotificationCategory
from ..access_token import EncodeToken, DecodeToken

bp_match = Blueprint('bp_match', __name__)

def getHourIndex(hourString):
    return datetime.strptime(hourString, '%H:%M').hour
    #return AvailableHours.query.filter_by(HourString=hourString).first().IdAvailableHours

def getHourString(hourIndex):
    print(hourIndex)
    print(type(hourIndex))
    print(f"{hourIndex}:00")
    return f"{hourIndex}:00"#GAMBIARRA
    #return AvailableHours.query.filter_by(IdAvailableHours=hourIndex).first().HourString

def daterange(start_date, end_date):
    if start_date == end_date:
        yield start_date
    else:
        for n in range(int ((end_date - start_date).days)+1):
            yield start_date + timedelta(n)

#rota que retorna todas cidades do banco de dados(utilizada pra o usuário escolher a cidade que mora)
@bp_match.route("/GetAllCities", methods=["GET"])
def GetAllCities():
    statesList=[]

    states = db.session.query(State).all()

    for state in states:
        statesList.append(state.to_jsonWithCities())
    return jsonify({'States':statesList})

#rota que retorna todas cidades que tem estabelecimento cadastrado
@bp_match.route("/GetAvailableCities", methods=["GET"])
def GetAvailableCities():
    cities = db.session.query(City)\
            .join(Store, Store.IdCity == City.IdCity).distinct()

    states = db.session.query(State)\
            .filter(State.IdState.in_([city.IdState for city in cities])).distinct()
    
    statesList=[]

    for state in states:
        statesList.append(state.to_jsonWithFilteredCities([city.IdCity for city in cities]))

    return jsonify({'States':statesList})

    
#rota utilizada pra buscar horários e partidas abertas
@bp_match.route("/SearchCourts", methods=["POST"])
def SearchCourts():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessToken = request.json.get('AccessToken')
    sportId = int(request.json.get('IdSport'))
    cityId = request.json.get('IdCity')
    dateStart = datetime.strptime(request.json.get('DateStart'), '%d-%m-%Y')
    dateEnd = datetime.strptime(request.json.get('DateEnd'), '%d-%m-%Y')
    timeStart = request.json.get('TimeStart')
    timeEnd = request.json.get('TimeEnd')

    user = User.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN

    stores = db.session.query(Store).filter(Store.IdCity == cityId)\
                                    .filter(Store.IsApproved).all()

    storePhotos = db.session.query(StorePhoto).filter(StorePhoto.IdStore.in_([store.IdStore for store in stores])).all()

    #query de todas as quadras(não estabelecimento) que aceita o esporte solicitado
    courts = db.session.query(StoreCourt)\
                    .join(StoreCourtSport, StoreCourtSport.IdStoreCourt == StoreCourt.IdStoreCourt)\
                    .filter(StoreCourtSport.IdSport == sportId)\
                    .filter(StoreCourt.IdStore.in_(store.IdStore for store in stores)).all()

    #busca os horarios de todas as quadras e seus respectivos preços
    courtHours = db.session.query(StorePrice)\
                    .filter(StorePrice.IdStoreCourt.in_(court.IdStoreCourt for court in courts)).all()
                    

    matches = db.session.query(Match)\
                    .filter(Match.IdStoreCourt.in_(court.IdStoreCourt for court in courts))\
                    .filter(Match.Date.in_(daterange(dateStart.date(), dateEnd.date())))\
                    .filter(Match.Canceled == False) \
                    .filter(((Match.IdTimeBegin >= timeStart) & (Match.IdTimeBegin <= timeEnd)) | \
                            ((Match.IdTimeEnd > timeStart) & (Match.IdTimeEnd <= timeEnd)) | \
                            ((Match.IdTimeBegin < timeStart) & (Match.IdTimeEnd > timeStart))).all()
    
    searchWeekdays= []
    for searchDay in daterange(dateStart.date(), dateEnd.date()):
        if(searchDay.weekday() not in searchWeekdays):
            searchWeekdays.append(searchDay.weekday())
    #lembrando que aqui são as partidas mensalistas e os horários bloqueados recorrentemente
    recurrentMatches = db.session.query(RecurrentMatch)\
                    .filter(RecurrentMatch.IdStoreCourt.in_(court.IdStoreCourt for court in courts))\
                    .filter(RecurrentMatch.Weekday.in_(searchWeekdays))\
                    .filter(RecurrentMatch.Canceled == False)\
                    .filter(((RecurrentMatch.IdTimeBegin >= timeStart) & (Match.IdTimeBegin <= timeEnd)) | \
                            ((RecurrentMatch.IdTimeEnd > timeStart) & (RecurrentMatch.IdTimeEnd <= timeEnd)) | \
                            ((RecurrentMatch.IdTimeBegin < timeStart) & (RecurrentMatch.IdTimeEnd > timeStart))).all()

    #partidas abertas
    jsonOpenMatches = []
    for match in matches:
        if (match.OpenUsers == True) and (match.Canceled == False) and (match.IdSport == sportId):
            jsonOpenMatches.append(
                match.to_json_open_match(),
            )

    #horários livres
    jsonDates =[]
    IdStoresList = []
    for validDate in daterange(dateStart.date(), dateEnd.date()):
        jsonStores=[]
        
        for store in stores:
            
            #quadras do estabelecimento
            filteredCourts = [court for court in courts if court.IdStore == store.IdStore]
            
            #Pode acontecer de um estabelecimento já estar validado, mas sem quadras cadastradas, nesse caso nada é mostrado
            if(len(filteredCourts) > 0):
                storeOperationHours = [storeOperationHour for storeOperationHour in courtHours if \
                                    (storeOperationHour.IdStoreCourt == filteredCourts[0].IdStoreCourt) and\
                                    (storeOperationHour.Weekday == validDate.weekday()) and \
                                    ((storeOperationHour.IdAvailableHour >= timeStart) and (storeOperationHour.IdAvailableHour <= timeEnd)) and \
                                    (((validDate == datetime.today().date()) and (datetime.strptime(storeOperationHour.AvailableHour.HourString, '%H:%M').time() < datetime.now().time())) == False)\
                                    ]
                
                jsonStoreOperationHours =[]
                for storeOperationHour in storeOperationHours:
                    jsonAvailableCourts =[]
                    for filteredCourt in filteredCourts:
                        concurrentMatch = [match for match in matches if \
                                    (match.IdStoreCourt ==  filteredCourt.IdStoreCourt) and \
                                    (match.Canceled == False) and \
                                    (match.Date == validDate) and \
                                    ((match.IdTimeBegin == storeOperationHour.IdAvailableHour) or \
                                    ((match.IdTimeBegin < storeOperationHour.IdAvailableHour) and (match.IdTimeEnd > storeOperationHour.IdAvailableHour)))\
                                    ]
                        concurrentRecurrentMatch = [recurrentMatch for recurrentMatch in recurrentMatches if \
                                    (recurrentMatch.IdStoreCourt ==  filteredCourt.IdStoreCourt) and \
                                    (recurrentMatch.Blocked == False) and \
                                    (recurrentMatch.Weekday == validDate.weekday()) and \
                                    ((recurrentMatch.IdTimeBegin == storeOperationHour.IdAvailableHour) or ((recurrentMatch.IdTimeBegin < storeOperationHour.IdAvailableHour) and (recurrentMatch.IdTimeEnd > storeOperationHour.IdAvailableHour)))\
                                    ]
                        concurrentBlockedHour = [recurrentMatch for recurrentMatch in recurrentMatches if \
                                    (recurrentMatch.IdStoreCourt ==  filteredCourt.IdStoreCourt) and \
                                    (recurrentMatch.Blocked == True) and \
                                    (recurrentMatch.Weekday == validDate.weekday()) and \
                                    ((recurrentMatch.IdTimeBegin == storeOperationHour.IdAvailableHour) or ((recurrentMatch.IdTimeBegin < storeOperationHour.IdAvailableHour) and (recurrentMatch.IdTimeEnd > storeOperationHour.IdAvailableHour)))\
                                    ]

                        #concurrentMatch para verificar que não tem partida marcada nesse dia e horario
                        #concurrentBlockedHour para verificar que horário não foi bloqueado
                        #concurrentRecurrentMatch é pra verificar se tem partida recorrente, mas tem um truque aqui
                        # se tem uma partida recorrente, as partidas do mes jáforam marcadas, então vão aparecer no concurrentMatch
                        # se alguma delas foi cancelada, por ex, o horário ainda poderia ser agendado.
                        if(not concurrentMatch) and (not concurrentBlockedHour) and (not(isCurrentMonth(validDate) == False and concurrentRecurrentMatch)):
                            jsonAvailableCourts.append({
                                'IdStoreCourt':filteredCourt.IdStoreCourt,
                                'Price': [int(courtHour.Price) for courtHour in courtHours if (courtHour.IdStoreCourt == filteredCourt.IdStoreCourt) and (courtHour.Weekday == validDate.weekday()) and (courtHour.IdAvailableHour == storeOperationHour.IdAvailableHour)][0]
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
            jsonDates.append({
                'Date':validDate.strftime('%d/%m/%Y'), 
                'Stores':jsonStores
                })
    

    return jsonify({'Dates':jsonDates, 'OpenMatches': jsonOpenMatches, 'Stores':[store.to_json() for store in stores]})
     

@bp_match.route("/GetUserMatches", methods=["POST"])
def GetUserMatches():
    if not request.json:
        abort(HttpCode.ABORT)

    tokenReq = request.json.get('AccessToken')

    user = db.session.query(User).filter(User.AccessToken == tokenReq).first()

    if user is None:
        return "Expired Token", HttpCode.EXPIRED_TOKEN

    userMatchesList = []
    #query para as partidas que o jogador jogou e vai jogar
    userMatches =  db.session.query(Match)\
                .join(MatchMember, Match.IdMatch == MatchMember.IdMatch)\
                .filter(MatchMember.IdUser == user.IdUser).all()

    for userMatch in userMatches:
        userMatchesList.append(userMatch.to_json())

    return jsonify({'UserMatches': userMatchesList}), HttpCode.SUCCESS


@bp_match.route("/MatchReservation", methods=["POST"])
def MatchReservation():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idStoreCourt = request.json.get('IdStoreCourt')
    sportId = request.json.get('SportId')
    date = datetime.strptime(request.json.get('Date'), '%d-%m-%Y')
    timeStart = int(request.json.get('TimeStart'))
    timeEnd = int(request.json.get('TimeEnd'))
    cost = request.json.get('Cost')

    concurrentMatch = Match.query.filter((Match.IdStoreCourt == int(idStoreCourt)) & (Match.Date == date) & (\
                ((Match.IdTimeBegin >= timeStart) & (Match.IdTimeBegin < timeEnd))  | \
                ((Match.IdTimeEnd > timeStart) & (Match.IdTimeEnd <= timeEnd))      | \
                ((Match.IdTimeBegin < timeStart) & (Match.IdTimeEnd > timeStart))   \
                )).first()

    #lembrando que aqui são as partidas mensalistas e os horários bloqueados recorrentemente
    concurrentRecurrentMatch = db.session.query(RecurrentMatch)\
                    .filter(RecurrentMatch.IdStoreCourt == int(idStoreCourt))\
                    .filter(RecurrentMatch.Weekday == date.weekday())\
                    .filter(RecurrentMatch.Canceled == False)\
                    .filter(((RecurrentMatch.IdTimeBegin >= timeStart) & (Match.IdTimeBegin <= timeEnd)) | \
                            ((RecurrentMatch.IdTimeEnd > timeStart) & (RecurrentMatch.IdTimeEnd <= timeEnd)) | \
                            ((RecurrentMatch.IdTimeBegin < timeStart) & (RecurrentMatch.IdTimeEnd > timeStart))).first()

    if (concurrentMatch is not None) or (concurrentRecurrentMatch is not None):
        return "Ops, esse horário não está mais disponível", HttpCode.WARNING
    else:
        user = User.query.filter_by(AccessToken = accessToken).first()

        if user is None:
            return '1', HttpCode.INVALID_ACCESS_TOKEN
        newMatch = Match(
            IdStoreCourt = idStoreCourt,
            IdSport = sportId,
            Date = date,
            IdTimeBegin = timeStart,
            IdTimeEnd = timeEnd,
            Cost = cost,
            OpenUsers = False,
            MaxUsers = 0,
            Canceled = False,
            CreationDate = datetime.now(),
            CreatorNotes = "",
            IdRecurrentMatch = 0,
            Blocked = False,
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
        return "Sua partida foi agendada!", HttpCode.ALERT

@bp_match.route("/GetMatchInfo", methods=["POST"])
def GetMatchInfo(): 

    matchUrl = request.json.get('MatchUrl')

    match = db.session.query(Match).filter(Match.MatchUrl == matchUrl).first()
    if match is None:
        return "Partida não encontrada", HttpCode.WARNING

    matchCounterList=[]
    for member in match.Members:
        matchCounter = db.session.query(Match)\
            .join(MatchMember, MatchMember.IdMatch == Match.IdMatch)\
            .filter(Match.IdSport == match.IdSport)\
            .filter(MatchMember.IdUser == member.User.IdUser)\
            .filter(MatchMember.WaitingApproval == False)\
            .filter(MatchMember.Refused == False)\
            .filter(MatchMember.Quit == False)\
            .filter(Match.Canceled == False)\
            .filter((Match.Date < datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.IdTimeEnd <= datetime.now().hour))).all()

        matchCounterList.append({
            'MatchCounter': len(matchCounter),
            'IdUser': member.User.IdUser,
        })

    return jsonify({'Match': match.to_json(), 'UsersMatchCounter':matchCounterList}), HttpCode.SUCCESS

@bp_match.route("/InvitationResponse", methods=["POST"])
def InvitationResponse():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idMatch = request.json.get('IdMatch')
    idUser = request.json.get('IdUser')
    accepted = request.json.get('Accepted')

    user = User.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return 'INVALID_ACCESS_TOKEN', HttpCode.WARNING

    match = Match.query.get(idMatch)
    if match is None:
        return "Partida não encontrada", HttpCode.WARNING
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (datetime.strptime(getHourString(match.IdTimeBegin), '%H:%M') < datetime.now())):
         return 'A partida já foi finalizada', HttpCode.WARNING
    else:
        matchMember = MatchMember.query.filter((MatchMember.IdMatch == idMatch) & (MatchMember.IdUser == idUser)).first()

        matchMember.WaitingApproval = False
        matchMember.Quit = False
        if accepted:
            matchMember.Refused = False
            idNotificationCategory = 3
        else:
            matchMember.Refused = True
            idNotificationCategory = 4
        newNotification = Notification(
            IdUser = idUser,
            IdUserReplaceText = user.IdUser,
            IdMatch = idMatch,
            IdNotificationCategory = idNotificationCategory,
            Seen = False
        )
        db.session.add(newNotification)
        db.session.commit()
        
        return "Ok",HttpCode.SUCCESS

@bp_match.route("/LeaveMatch", methods=["POST"])
def LeaveMatch():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idMatch = request.json.get('IdMatch')

    user = User.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return 'INVALID_ACCESS_TOKEN', HttpCode.WARNING

    match = Match.query.get(idMatch)
    if match is None:
        return "Partida não encontrada", HttpCode.WARNING
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (datetime.strptime(getHourString(match.IdTimeBegin), '%H:%M') < datetime.now())):
         return 'A partida já foi finalizada', HttpCode.WARNING
    else:
        matchMember = MatchMember.query.filter((MatchMember.IdMatch == idMatch) & (MatchMember.IdUser == user.IdUser)).first()
        matchMember.Quit=True
        matchMember.WaitingApproval=False
        matchMember.QuitDate=datetime.now()

        for member in match.Members:
            if member.IsMatchCreator == True:
                newNotification = Notification(
                    IdUser = member.IdUser,
                    IdUserReplaceText = matchMember.IdUser,
                    IdMatch = idMatch,
                    IdNotificationCategory = 8,
                    Seen = False
                )
                db.session.add(newNotification)
                break
        db.session.commit()
        return "Você saiu da partida",HttpCode.ALERT

@bp_match.route("/SaveCreatorNotes", methods=["POST"])
def SaveCreatorNotes():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idMatch = request.json.get('IdMatch')
    newCreatorNotes = request.json.get('NewCreatorNotes')

    user = User.query.filter_by(AccessToken = accessToken).first()

    if user is None:
        return 'Sessão inválida', HttpCode.WARNING

    match = db.session.query(Match).get(idMatch)
    if match is None:
        return 'Partida não encontrada', HttpCode.WARNING
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (datetime.strptime(getHourString(match.IdTimeBegin), '%H:%M') < datetime.now())):
         return 'Partida já foi finalizada', HttpCode.WARNING
    else:
        match.CreatorNotes = newCreatorNotes
        db.session.commit()
        return "Seu recado foi atualizado",HttpCode.ALERT

@bp_match.route("/SaveOpenMatch", methods=["POST"])
def SaveOpenMatch():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idMatch = request.json.get('IdMatch')
    isOpenMatch = request.json.get('IsOpenMatch')
    maxUsers = request.json.get('MaxUsers')

    user = User.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return 'Sessão inválida', HttpCode.WARNING

    match = db.session.query(Match).get(idMatch)
    if match is None:
        return 'Partida não encontrada', HttpCode.WARNING
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (datetime.strptime(getHourString(match.IdTimeBegin), '%H:%M') < datetime.now())):
         return 'Partida já foi finalizada', HttpCode.WARNING
    else:
        match.OpenUsers = isOpenMatch
        if isOpenMatch == False:
            match.MaxUsers = 0
        else:
            match.MaxUsers = maxUsers
        db.session.commit()
        return "Sua partida foi alterada!",HttpCode.ALERT


@bp_match.route("/JoinMatch", methods=["POST"])
def JoinMatch():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idMatch = request.json.get('IdMatch')

    user = User.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return 'Token inválido', HttpCode.WARNING

    match = db.session.query(Match).get(idMatch)
    if match is None:
        return 'Partida não encontrada', HttpCode.WARNING
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (datetime.strptime(getHourString(match.IdTimeBegin), '%H:%M') < datetime.now())):
         return 'A partida já foi finalizada', HttpCode.WARNING
    else:
        matchMember = db.session.query(MatchMember).filter((MatchMember.IdMatch == idMatch) & (MatchMember.IdUser == user.IdUser)).first()
        if matchMember is None:
            newMatchMember = MatchMember(
                IdUser = user.IdUser,
                IsMatchCreator = False,
                WaitingApproval = True,
                Refused = False,
                IdMatch = idMatch,
                EntryDate = datetime.now(),
                Quit = False
            )
            db.session.add(newMatchMember)

        else:
            matchMember.IdUser = user.IdUser
            matchMember.IsMatchCreator = False
            matchMember.WaitingApproval = True
            matchMember.Refused = False
            matchMember.IdMatch = idMatch
            matchMember.EntryDate = datetime.now()
            matchMember.Quit = False
        
        matchCreator = db.session.query(MatchMember).filter((MatchMember.IdMatch == idMatch) & (MatchMember.IsMatchCreator == True)).first()
        newNotification = Notification(
            IdUser = matchCreator.IdUser,
            IdUserReplaceText = user.IdUser,
            IdMatch = idMatch,
            IdNotificationCategory = 1,
            Seen = False
        )
        db.session.add(newNotification)
        newNotification = Notification(
            IdUser = user.IdUser,
            IdUserReplaceText = matchCreator.IdUser,
            IdMatch = idMatch,
            IdNotificationCategory = 2,
            Seen = False
        )
        db.session.add(newNotification)
        db.session.commit()
        return "Solicitação enviada",HttpCode.ALERT

@bp_match.route("/CancelMatch", methods=["POST"])
def CancelMatch():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idMatch = request.json.get('IdMatch')

    user = User.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return 'Token inválido', HttpCode.WARNING

    match = Match.query.get(idMatch)
    if match is None:
        return 'Partida não encontrada', HttpCode.WARNING
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (datetime.strptime(getHourString(match.IdTimeBegin), '%H:%M') < datetime.now())):
         return 'A partida já foi finalizada', HttpCode.WARNING
    else:
        CanCancelUpTo = datetime.strptime(match.TimeBegin.HourString, '%H:%M').replace(year=match.Date.year,month=match.Date.month,day=match.Date.day) - timedelta(hours=match.StoreCourt.Store.HoursBeforeCancellation)
        if datetime.now() >  CanCancelUpTo:
            return 'Não é mais possível cancelar a partida', HttpCode.WARNING
        
        match.Canceled = True

        matchMembers = MatchMember.query.filter(MatchMember.IdMatch == idMatch)\
                                .filter(MatchMember.WaitingApproval == False)\
                                .filter(MatchMember.Refused == False)\
                                .filter(MatchMember.Quit == False).all()
        for matchMember in matchMembers:
            matchMember.Quit=True
            matchMember.QuitDate=datetime.now()
            if matchMember.IsMatchCreator == True:
                idNotificationCategory = 6
            else:
                idNotificationCategory = 7
            if matchMember.Refused == False:
                newNotification = Notification(
                    IdUser = matchMember.IdUser,
                    IdUserReplaceText = matchMember.IdUser,
                    IdMatch = idMatch,
                    IdNotificationCategory = idNotificationCategory,
                    Seen = False
                )
                db.session.add(newNotification)
                db.session.commit()
        return "Partida cancelada",HttpCode.ALERT

@bp_match.route("/CancelMatchEmployee", methods=["POST"])
def CancelMatchEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    idMatchReq = request.json.get('IdMatch')
    cancelationReasonReq = request.json.get('CancelationReason')

    #busca a loja a partir do token do employee
    storeCourt = db.session.query(StoreCourt).\
            join(Employee, Employee.IdStore == StoreCourt.IdStore)\
            .filter(Employee.AccessToken == accessTokenReq).first()
    
    #Caso não encontrar Token
    if storeCourt is None:
        return webResponse("Token não encontrado", None), HttpCode.WARNING

    match = Match.query.get(idMatchReq)
    if match is None:
        return 'Partida não encontrada', HttpCode.WARNING
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (datetime.strptime(getHourString(match.IdTimeBegin), '%H:%M') < datetime.now())):
         return 'A partida já foi finalizada', HttpCode.WARNING
    else:
        
        match.Canceled = True
        match.BlockedReason = cancelationReasonReq

        matchMembers = MatchMember.query.filter(MatchMember.IdMatch == idMatchReq)\
                        .filter(MatchMember.WaitingApproval == False)\
                        .filter(MatchMember.Refused == False)\
                        .filter(MatchMember.Quit == False).all()
        for matchMember in matchMembers:
            matchMember.Quit=True
            matchMember.QuitDate=datetime.now()

            newNotification = Notification(
                IdUser = matchMember.IdUser,
                IdUserReplaceText = matchMember.IdUser,
                IdMatch = idMatchReq,
                IdNotificationCategory = 9,
                Seen = False
            )
            db.session.add(newNotification)

        db.session.commit()

        matchDatetime = datetime(match.Date.year, match.Date.month, match.Date.day)

        startDate = lastSundayOnLastMonth(matchDatetime)
        endDate = firstSundayOnNextMonth(matchDatetime)

        courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == storeCourt.IdStore).all()

        matches = db.session.query(Match).filter(Match.IdStoreCourt.in_([court.IdStoreCourt for court in courts]))\
        .filter((Match.Date >= startDate) & (Match.Date <= endDate))\
        .filter(Match.Canceled == False).all()
        
        matchList =[]
        for match in matches:
            matchList.append(match.to_json_min())

        return jsonify({"Matches": matchList}), HttpCode.SUCCESS

@bp_match.route("/RemoveMatchMember", methods=["POST"])
def RemoveMatchMember():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idMatch = request.json.get('IdMatch')
    idUserDelete = request.json.get('IdUser')

    user = User.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return 'Token inválido', HttpCode.WARNING

    match = Match.query.get(idMatch)
    if match is None:
        return 'Partida não encontrada', HttpCode.WARNING
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (datetime.strptime(getHourString(match.IdTimeBegin), '%H:%M') < datetime.now())):
         return 'A partida já foi finalizada', HttpCode.WARNING
    else:

        matchMember = MatchMember.query.filter((MatchMember.IdMatch == idMatch) & (MatchMember.IdUser == idUserDelete)).first()
        matchCreator = MatchMember.query.filter((MatchMember.IdMatch == idMatch) & (MatchMember.IsMatchCreator == True)).first()

        matchMember.Refused = True
        matchMember.Quit = True
        matchMember.WaitingApproval = False
        matchMember.QuitDate = datetime.now()
        newNotification = Notification(
            IdUser = idUserDelete,
            IdUserReplaceText = matchCreator.IdUser,
            IdMatch = idMatch,
            IdNotificationCategory = 5,
            Seen = False
        )
        db.session.add(newNotification)

        db.session.commit()
        return "Jogador removido",HttpCode.ALERT

@bp_match.route("/AddMatch", methods=["POST"])
def AddMatch():
    if not request.json:
        abort(400)
    match = Match(
        IdStore = request.json.get('IdStore'),
        Date = request.json.get('Date'),
        IdTimeBegin = request.json.get('TimeBegin'),
        IdTimeEnd = request.json.get('TimeEnd'),
        Cost = request.json.get('Cost'),
        OpenUsers = request.json.get('OpenUsers'),
        MaxUsers = request.json.get('MaxUsers'),
        Canceled = request.json.get('Canceled'),
    )
    db.session.add(match)
    db.session.commit()
    return jsonify(match.to_json()), HttpCode.SUCCESS
    

@bp_match.route("/GetOpenMatches", methods=["POST"])
def GetOpenMatches():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessToken = request.json.get('accessToken')

    user = User.query.filter_by(AccessToken = accessToken).first()

    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN

    openMatches = db.session.query(Match)\
                .join(StoreCourt, StoreCourt.IdStoreCourt == Match.IdStoreCourt)\
                .join(Store, Store.IdStore == StoreCourt.IdStore)\
                .filter(Match.OpenUsers == True)\
                .filter((Match.Date > datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.IdTimeBegin >= int(datetime.now().strftime("%H")))))\
                .filter(Match.Canceled == False)\
                .filter(Match.IdSport == user.IdSport)\
                .filter(Store.IdCity == user.IdCity).all()
    
    jsonOpenMatches = []
    for openMatch in openMatches:
        jsonOpenMatches.append(openMatch.to_json())

    return jsonify({'OpenMatches': jsonOpenMatches}), HttpCode.SUCCESS
    # storeList = []

    # for openMatch in openMatches:
    #     userAlreadyInMatch = False
    #     matchMemberCounter = 0
    #     for member in openMatch.Members:
    #         #get matchCreator info
    #         if member.IsMatchCreator == True:
    #             matchCreator = member.User
    #             for rank in matchCreator.Ranks:
    #                 if rank.RankCategory.IdSport == openMatch.IdSport:
    #                     matchCreatorRank = rank

    #         if (member.User.IdUser == userLogin.IdUser) and (member.Quit == False) and (member.WaitingApproval == False):
    #             userAlreadyInMatch = True
    #             break
    #         else:
    #             if (member.WaitingApproval == False) and (member.Refused == False) and (member.Quit == False):
    #                 matchMemberCounter +=1
    #     if (userAlreadyInMatch == False) and (matchMemberCounter < openMatch.MaxUsers):
    #         jsonOpenMatches.append({
    #             'MatchDetails':openMatch.to_json(),
    #             'MatchCreator': matchCreator.identification_to_json(),
    #             'SlotsRemaining': openMatch.MaxUsers - matchMemberCounter,
    #             'MatchCreatorRank':matchCreatorRank.to_json()
    #         })
    #         if len(storeList) == 0:
    #             storeList.append(openMatch.StoreCourt.Store)
    #         else:
    #             if openMatch.StoreCourt.Store not in storeList:
    #                 storeList.append(openMatch.StoreCourt.Store)
        
    #     distinctStores = []
    #     for store in storeList:
    #         distinctStores.append({
    #             'Store': store.to_json(),
    #             'StorePhoto': [photo.to_json() for photo in store.Photos]
    #             })

    # return jsonify({'OpenMatches': jsonOpenMatches, 'Stores':distinctStores}), HttpCode.SUCCESS


@bp_match.route('/BlockUnblockHour', methods=['POST'])
def BlockUnblockHour():
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
    dateReq = datetime.strptime(request.json.get('Date'), '%d/%m/%Y')

    match = db.session.query(Match)\
                .filter(Match.Date == dateReq)\
                .filter((Match.IdTimeBegin == idHourReq) | ((Match.IdTimeBegin < idHourReq) & (Match.IdTimeEnd > idHourReq)))\
                .filter(Match.IdStoreCourt == idStoreCourtReq).first()


    blockedReq = request.json.get('Blocked')
    blockedReasonReq = request.json.get('BlockedReason')

    if match is None:
        newMatch = Match(
            IdStoreCourt = idStoreCourtReq,
            IdSport = None,
            Date = dateReq,
            IdTimeBegin = idHourReq,
            IdTimeEnd = idHourReq+1,
            Cost = 0,
            OpenUsers = False,
            MaxUsers = 0,
            Canceled = False,
            CreationDate = datetime.now(),
            CreatorNotes = "",
            IdRecurrentMatch = None,
            Blocked = blockedReq,
            BlockedReason = blockedReasonReq,
        )
        db.session.add(newMatch)

    else:
        #se tinha alguma partida com custo != 0 quer dizer q alguem agendou uma partida nesse meio tempo, ai não pode mais bloear o horario
        if match.Cost != 0:
            return webResponse("Ops", "Não foi possível bloquear o horário. Uma partida já foi marcada"), HttpCode.WARNING
        
        #em teoria se chegou aqui é para desbloquear um horário, coloquei esse if só pra ter certeza
        if blockedReq == False:
            db.session.delete(match)
    
    db.session.commit()

    startDate = lastSundayOnLastMonth(dateReq)
    endDate = firstSundayOnNextMonth(dateReq)

    courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == storeCourt.IdStore).all()

    matches = db.session.query(Match).filter(Match.IdStoreCourt.in_([court.IdStoreCourt for court in courts]))\
    .filter((Match.Date >= startDate) & (Match.Date <= endDate))\
    .filter(Match.Canceled == False).all()
    
    matchList =[]
    for match in matches:
        matchList.append(match.to_json_min())

    return jsonify({"Matches": matchList}), HttpCode.SUCCESS

@bp_match.route("/match/<id>", methods=["GET"])
def match(id):
    match = match = Match.query.get(id)
    return match.to_json()

@bp_match.route('/SearchCustomMatches', methods=['POST'])
def SearchCustomMatches():

    accessTokenReq = request.json.get('AccessToken')
    dateStartReq = datetime.strptime(request.json.get('DateStart'), '%d/%m/%Y')
    dateEndReq = datetime.strptime(request.json.get('DateEnd'), '%d/%m/%Y')

    employee = db.session.query(Employee).filter(Employee.AccessToken == accessTokenReq).first()

    if employee is None:
        return '1', HttpCode.EXPIRED_TOKEN
    
    matches = db.session.query(Match)\
                    .filter(Match.IdStoreCourt.in_([court.IdStoreCourt for court in employee.Store.Courts]))\
                    .filter((Match.Date >= dateStartReq) & (Match.Date <= dateEndReq))\
                    .filter(Match.Canceled == False)\
                    .filter(Match.Blocked != True).all()

    matchList = []
    for match in matches:
        matchList.append(match.to_json_min())

    return {'Matches': matchList}, HttpCode.SUCCESS