from flask import Blueprint, jsonify, abort, request, json
from datetime import datetime, timedelta, date
from sqlalchemy import func 
from ..extensions import db
import os
from ..responses import webResponse
from ..utils import firstSundayOnNextMonth, lastSundayOnLastMonth, isCurrentMonth
from ..routes.store_routes import getAvailableStores
from ..Models.http_codes import HttpCode
from ..Models.match_model import Match, queryMatchesForCourts
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
from ..Models.employee_model import Employee, getStoreCourtByToken, getEmployeeByToken
from ..Models.store_court_sport_model import StoreCourtSport
from ..Models.sport_model import Sport
from ..Models.user_model import User
from ..Models.user_credit_card_model import UserCreditCard
from ..Models.notification_user_model import NotificationUser
from ..Models.notification_user_category_model import NotificationUserCategory
from ..Models.notification_store_model import NotificationStore
from ..Models.notification_store_category_model import NotificationStoreCategory
from ..Models.coupon_model import Coupon
from ..access_token import EncodeToken, DecodeToken
from ..emails import emailUserMatchConfirmed, emailUserReceiveCoupon, emailStoreMatchConfirmed, emailStoreMatchCanceled
from ..Asaas.Customer.update_customer import updateCpf
from ..Asaas.Payment.create_payment import createPaymentPix, createPaymentCreditCard, getSplitPercentage
from ..Asaas.Payment.refund_payment import refundPayment
from ..Asaas.Payment.generate_qr_code import generateQrCode
from sandfriends_backend.push_notifications import \
                sendMatchInvitationNotification,\
                sendMatchInvitationRefusedNotification,\
                sendMatchInvitationAcceptedNotification,\
                sendMemberLeftMatchNotification,\
                sendMatchCanceledFromCreatorNotification,\
                sendEmployeesNewMatchNotification,\
                sendStudentConfirmedClassNotification,\
                sendStudentUnconfirmedClassNotification,\
                sendClassCanceledByTeacher
from sqlalchemy import or_
from ..routes.coupon_routes import generateRandomCouponCode

bp_match = Blueprint('bp_match', __name__)

def getHourIndex(hourString):
    return datetime.strptime(hourString, '%H:%M').hour
    #return AvailableHours.query.filter_by(HourString=hourString).first().IdAvailableHours

def getHourString(hourIndex):
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

def GetAvailableCitiesList():
    stores = getAvailableStores()
    
    cities = db.session.query(City)\
            .filter(City.IdCity.in_([store.IdCity for store in stores])).distinct()

    states = db.session.query(State)\
            .filter(State.IdState.in_([city.IdState for city in cities])).distinct()
    
    statesList=[]

    for state in states:
        statesList.append(state.to_jsonWithFilteredCities([city.IdCity for city in cities]))

    return statesList

#rota que retorna todas cidades que tem estabelecimento cadastrado
@bp_match.route("/GetAvailableCities", methods=["GET"])
def GetAvailableCities():
    return jsonify({'States':GetAvailableCitiesList()})

#rota para buscar quadras em uma cidade
@bp_match.route("/SearchStores", methods=["POST"])
def SearchStores():
    # if not request.json:
    #     abort(HttpCode.ABORT)

    idCityReq = request.json.get('IdCity')
    idSportReq = request.json.get('IdSport')

    stores = db.session.query(Store)\
                .filter(Store.IdCity == idCityReq).all()


    storesList = []
    for store in stores:
        if store.IsAvailable:
            storesList.append(store.to_json())

    return jsonify({'Stores': storesList}), HttpCode.SUCCESS

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
    searchIdStore = request.json.get('IdStore')

    #esse user pode ser nulo pq busca pelo web não precisa estar logado
    user = User.query.filter_by(AccessToken = accessToken).first()

    stores = db.session.query(Store).filter(Store.IdCity == cityId)\
                                    .filter(Store.IdStore.in_([store.IdStore for store in getAvailableStores()])).all()
    storeAux =[]
    for store in stores:
        if (searchIdStore is not None and store.IdStore == searchIdStore or searchIdStore is None) and store.IsAvailable == True:
            storeAux.append(store)
    stores = storeAux

    #query de todas as quadras(não estabelecimento) que aceita o esporte solicitado
    courts = db.session.query(StoreCourt)\
                    .join(StoreCourtSport, StoreCourtSport.IdStoreCourt == StoreCourt.IdStoreCourt)\
                    .filter(StoreCourtSport.IdSport == sportId)\
                    .filter(StoreCourt.IdStore.in_(store.IdStore for store in stores)).all()

    #busca os horarios de todas as quadras e seus respectivos preços
    courtHours = db.session.query(StorePrice)\
                    .filter(StorePrice.IdStoreCourt.in_(court.IdStoreCourt for court in courts)).all()

    
    searchWeekdays= []
    for searchDay in daterange(dateStart.date(), dateEnd.date()):
        if(searchDay.weekday() not in searchWeekdays):
            searchWeekdays.append(searchDay.weekday())
   
    idStoreCourts = [court.IdStoreCourt for court in courts]
    matches = queryConcurrentMatches(idStoreCourts, daterange(dateStart.date(), dateEnd.date()), timeStart, timeEnd)
    recurrentMatches = queryConcurrentRecurrentMatches(idStoreCourts, searchWeekdays, timeStart, timeEnd)

    #partidas abertas
    jsonOpenMatches = []
    for match in matches:
        if (match.OpenUsers == True) and (match.Canceled == False) and (match.IdSport == sportId):
            userAlreadyInMatch = False
            matchMemberCounter = 0
            for member in match.Members:
                if user is not None:
                    if (member.User.IdUser == user.IdUser)  and (member.Refused == False) and (member.Quit == False):
                        userAlreadyInMatch = True
                        break
            if (userAlreadyInMatch == False) and (matchMemberCounter < match.MaxUsers):
                jsonOpenMatches.append(
                    match.to_json_open_match(),
                )

    #Monta o retorno com os horários livres
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
                        
                        #Indicadires de partidas já agendadas - conflito de horário
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
                                    ((recurrentMatch.IdTimeBegin == storeOperationHour.IdAvailableHour) or \
                                        ((recurrentMatch.IdTimeBegin < storeOperationHour.IdAvailableHour) and (recurrentMatch.IdTimeEnd > storeOperationHour.IdAvailableHour)))\
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
                        # if(not concurrentMatch) and \
                        #     (not concurrentBlockedHour) and \
                        #     (not( not(isCurrentMonth(validDate)) and concurrentRecurrentMatch )):
                        if isHourAvailableForMatch(matches, recurrentMatches, filteredCourt.IdStoreCourt, validDate, storeOperationHour.IdAvailableHour):
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
        return "Expired Token " + str(tokenReq), HttpCode.EXPIRED_TOKEN

    userMatchesList = []
    #query para as partidas que o jogador jogou e vai jogar
    userMatches =  db.session.query(Match)\
                .join(MatchMember, Match.IdMatch == MatchMember.IdMatch)\
                .filter(MatchMember.IdUser == user.IdUser).all()


    for userMatch in userMatches:
        userMatchesList.append(userMatch.to_json())

    return jsonify({'UserMatches': userMatchesList}), HttpCode.SUCCESS

#Faz a reserva de uma partida
@bp_match.route("/MatchReservation", methods=["POST"])
def MatchReservation():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    phoneNumberReq = request.json.get('PhoneNumber')
    idStoreCourtReq = request.json.get('IdStoreCourt')
    sportIdReq = request.json.get('SportId')
    dateReq = datetime.strptime(request.json.get('Date'), '%d/%m/%Y')
    timeStartReq = int(request.json.get('TimeStart'))
    timeEndReq = int(request.json.get('TimeEnd'))
    costReq = request.json.get('Cost')
    paymentReq = request.json.get('Payment')
    cpfReq = request.json.get('Cpf')
    idCouponReq = request.json.get('IdCoupon')
    
    if request.json.get("IdCreditCard")== "": 
        idCreditCardReq =  None 
    else: 
        idCreditCardReq = request.json.get("IdCreditCard")
        cvvReq = request.json.get("Cvv")

    user = User.query.filter_by(AccessToken = accessTokenReq).first()

    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN
    
    #Verifica se já tem uma partida agendada no mesmo horário
    concurrentMatch = queryConcurrentMatches([idStoreCourtReq],[dateReq], timeStartReq, timeEndReq)
    concurrentRecurrentMatches = queryConcurrentRecurrentMatches([idStoreCourtReq], [dateReq], timeStartReq, timeEndReq)

    #Caso o horário não esteja mais disponível na hora dele fazer a reserva
    if isHourAvailableForMatch(concurrentMatch, concurrentRecurrentMatches, idStoreCourtReq, dateReq, timeStartReq) == False:
        return f"Ops, esse horário não está mais disponível", HttpCode.WARNING
    
    asaasPaymentId = None
    asaasBillingType = None
    asaasPaymentStatus = None
    asaasPixCode = None
    costFinalReq = None
    costAsaasTaxReq = None
    costSandfriendsNetTaxReq = None
    asaasSplitReq = None

    #Busca a quadra que vai ser feita a cobrança
    store = db.session.query(Store)\
            .join(StoreCourt, StoreCourt.IdStore == Store.IdStore)\
            .filter(StoreCourt.IdStoreCourt == idStoreCourtReq).first()
    
    #Busca o cupom de desconto
    coupon = db.session.query(Coupon).filter(Coupon.IdCoupon == idCouponReq).first()

    #### PIX
    if paymentReq == 1:
        if cpfReq != user.Cpf:
            user.Cpf = cpfReq
            db.session.commit()
            #Atualiza o CPF do usuário do Asaas - necessário pra fazer o pagamento
            responseCpf = updateCpf(user)

            if responseCpf.status_code != 200:
                return "Ops, verifique se seu CPF está correto.", HttpCode.WARNING

        #Calcular o valor do desconto do cupom
        discountValue = 0
        if coupon is not None:
            if coupon.DiscountType == "PERCENTAGE":
                discountValue = (costReq * float(coupon.Value))/100
            if coupon.DiscountType == "FIXED":
                discountValue = float(coupon.Value)

        costUser = float(costReq - discountValue)

        #Verifica se ficou negativo
        if costUser <= 0:
            costUser = 0    

        #Gera a cobrança no Asaas
        responsePayment = createPaymentPix(user, costUser, store)
        if responsePayment.status_code != 200:
            return "Não foi possível processar seu pagamento. Tente novamente", HttpCode.WARNING

        #Obtém o código para pagamento do Pix
        responsePixCode = generateQrCode(responsePayment.json().get('id'))

        if responsePixCode.status_code == 200:
            asaasPixCode = responsePixCode.json().get('payload')
        
        #Dados que retornam do Asaas
        asaasPaymentStatus = "PENDING"
        asaasPaymentId = responsePayment.json().get('id')
        asaasBillingType = responsePayment.json().get('billingType')
        #Valor final, após Split - o que a quadra irá receber
        costFinalReq = responsePayment.json().get('split')[0].get('totalValue')
        #Valor da taxa do Asaas
        costNetReq = responsePayment.json().get('netValue')
        costUserReq = responsePayment.json().get('value')
        costAsaasTaxReq = costUserReq - costNetReq
        #Valor da remuneração do Sandfriends
        costSandfriendsNetTaxReq = costUserReq - costAsaasTaxReq - costFinalReq
        #Porcentagem do Split
        asaasSplitReq = responsePayment.json().get('split')[0].get('percentualValue')

    #### CARTÃO DE CRÉDITO
    elif paymentReq == 2:
        creditCard = db.session.query(UserCreditCard).filter(UserCreditCard.IdUserCreditCard == idCreditCardReq).first()

        if creditCard is None:
            return "Não foi possível processar seu pagamento. Tente novamente", HttpCode.WARNING
        
        #Calcular o valor do desconto do cupom
        discountValue = 0
        if coupon is not None:
            if coupon.DiscountType == "PERCENTAGE":
                discountValue = (costReq * float(coupon.Value))/100
            if coupon.DiscountType == "FIXED":
                discountValue = float(coupon.Value)

        costUser = float(costReq - discountValue)

        #Verifica se ficou negativo
        if costUser < 0:
            costUser = 0

        #Gera a cobrança no Asaas
        responsePayment = createPaymentCreditCard(
            user = user, 
            creditCard = creditCard,
            value = costUser,
            store = store,
            cvv = cvvReq
        )
        
        if responsePayment.status_code != 200:
            return "Não foi possível processar seu pagamento. Tente novamente", HttpCode.WARNING

        #Dados que retornam do Asaas
        asaasPaymentStatus = "PENDING"
        asaasPaymentId = responsePayment.json().get('id')
        asaasBillingType = responsePayment.json().get('billingType')
        #Valor final, após Split - o que a quadra irá receber
        costFinalReq = responsePayment.json().get('split')[0].get('totalValue')
        #Valor da taxa do Asaas
        costNetReq = responsePayment.json().get('netValue')
        costUserReq = responsePayment.json().get('value')
        costAsaasTaxReq = costUserReq - costNetReq
        #Valor da remuneração do Sandfriends
        costSandfriendsNetTaxReq = costUserReq - costAsaasTaxReq - costFinalReq
        #Porcentagem do Split
        asaasSplitReq = responsePayment.json().get('split')[0].get('percentualValue')

    #### PAGAMENTO NO LOCAL
    elif paymentReq == 3:
        asaasBillingType = "PAY_IN_STORE"
        asaasPaymentStatus = "CONFIRMED"

        costFinalReq = costReq
        costUserReq = costReq
        costAsaasTaxReq = 0
        costSandfriendsNetTaxReq = 0
        asaasSplitReq = 0
        discountValue = 0
    else:
        return "Forma de pagamento inválida", HttpCode.WARNING
    
    #Cria a partida
    newMatch = Match(
        IdStoreCourt = idStoreCourtReq,
        IdSport = sportIdReq,
        Date = dateReq,
        IdTimeBegin = timeStartReq,
        IdTimeEnd = timeEndReq,
        Cost = costReq,
        OpenUsers = False,
        MaxUsers = 0,
        Canceled = False,
        CreationDate = datetime.now(),
        CreatorNotes = "",
        IdRecurrentMatch = 0,
        Blocked = False,
        BlockedReason = "",
        AsaasPaymentId = asaasPaymentId,
        AsaasBillingType = asaasBillingType,
        AsaasPaymentStatus = asaasPaymentStatus,
        AsaasPixCode = asaasPixCode,
        IdUserCreditCard = idCreditCardReq,
        CostFinal = costFinalReq,
        CostAsaasTax = costAsaasTaxReq,
        CostSandfriendsNetTax = costSandfriendsNetTaxReq,
        AsaasSplit = asaasSplitReq,
        IdCoupon  = idCouponReq,
        CostDiscount = discountValue,
        CostUser = costUserReq
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
        HasPaid = True,
        Cost = 0,
    )
    db.session.add(matchMember)

    db.session.commit()
    db.session.refresh(newMatch)

    #Se for pagamento no local, já envia notificação pra quadra sobre o agendamento
    if paymentReq == 3:
        #Notificação para a loja
        newNotificationStore = NotificationStore(
            IdUser = newMatch.matchCreator().IdUser,
            IdStore = newMatch.StoreCourt.IdStore,
            IdMatch = newMatch.IdMatch,
            IdNotificationStoreCategory = 1,
            EventDatetime = datetime.now()
        )
        db.session.add(newNotificationStore)
        db.session.commit()
        #Envia o e-mail para o jogador
        emailUserMatchConfirmed(newMatch,)
        #Envia a notificação para o app das quadras
        sendEmployeesNewMatchNotification(newMatch, newMatch.StoreCourt.Store.Employees)
        #Envia o e-mail para a quadra
        emailStoreMatchConfirmed(newMatch)

    #PIX
    if paymentReq == 1:
        return jsonify({'Message':"Sua partida foi reservada!", "Pixcode": asaasPixCode}), HttpCode.SUCCESS
    else:
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
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (match.IsFinished())):
         return 'A partida já foi finalizada', HttpCode.WARNING
    else:
        matchMember = MatchMember.query.filter((MatchMember.IdMatch == idMatch) & (MatchMember.IdUser == idUser)).first()
        matchCreator = MatchMember.query.filter((MatchMember.IdMatch == idMatch) & (MatchMember.IsMatchCreator == True)).first()

        matchMember.WaitingApproval = False
        matchMember.Quit = False
        if accepted:
            matchMember.Refused = False
            idNotificationUserCategory = 3
        else:
            matchMember.Refused = True
            idNotificationUserCategory = 4
        newNotificationUser = NotificationUser(
            IdUser = idUser,
            IdUserReplaceText = user.IdUser,
            IdMatch = idMatch,
            IdNotificationUserCategory = idNotificationUserCategory,
            Seen = False
        )
        db.session.add(newNotificationUser)
        db.session.commit()
        
        if accepted:
            sendMatchInvitationAcceptedNotification(matchCreator.User, matchMember.User, match)
        else:
            sendMatchInvitationRefusedNotification(matchCreator.User, matchMember.User, match)
        return "Ok",HttpCode.SUCCESS

#Sai da partida
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
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (match.IsFinished())):
         return 'A partida já foi finalizada', HttpCode.WARNING
    else:
        matchMember = MatchMember.query.filter((MatchMember.IdMatch == idMatch) & (MatchMember.IdUser == user.IdUser)).first()
        matchMember.Quit=True
        matchMember.WaitingApproval=False
        matchMember.QuitDate=datetime.now()
        matchMember.HasPaid = False

        if match.IsClass:
            IdNotif = 11
        else:
            IdNotif = 8

        for member in match.Members:
            if member.IsMatchCreator == True:
                newNotificationUser = NotificationUser(
                    IdUser = member.IdUser,
                    IdUserReplaceText = matchMember.IdUser,
                    IdMatch = idMatch,
                    IdNotificationUserCategory = IdNotif,
                    Seen = False
                )
                db.session.add(newNotificationUser)
                break
        db.session.commit()

        if match.IsClass:
            sendStudentUnconfirmedClassNotification(match.matchCreator().User, matchMember.User, match)
        else:
            sendMemberLeftMatchNotification(match.matchCreator().User, matchMember.User, match)
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
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (match.IsFinished())):
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
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (match.IsFinished())):
         return str(match.IsFinished()), HttpCode.WARNING
         #return 'Partida já foi finalizada', HttpCode.WARNING
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
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (match.IsFinished())):
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
                Quit = False,
                HasPaid = False,
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
            matchMember.HasPaid = False
        
        matchCreator = db.session.query(MatchMember).filter((MatchMember.IdMatch == idMatch) & (MatchMember.IsMatchCreator == True)).first()
        newNotificationUser = NotificationUser(
            IdUser = matchCreator.IdUser,
            IdUserReplaceText = user.IdUser,
            IdMatch = idMatch,
            IdNotificationUserCategory = 1,
            Seen = False
        )
        db.session.add(newNotificationUser)
        newNotificationUser = NotificationUser(
            IdUser = user.IdUser,
            IdUserReplaceText = matchCreator.IdUser,
            IdMatch = idMatch,
            IdNotificationUserCategory = 2,
            Seen = False
        )
        db.session.add(newNotificationUser)
        db.session.commit()

        sendMatchInvitationNotification(matchCreator.User, user, match)
        return "Solicitação enviada",HttpCode.ALERT


@bp_match.route("/JoinClass", methods=["POST"])
def JoinClass():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idMatch = request.json.get('IdMatch')

    user = User.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return 'Token inválido', HttpCode.WARNING

    match = db.session.query(Match).get(idMatch)
    if match is None:
        return 'Aula não encontrada', HttpCode.WARNING
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (match.IsFinished())):
        return 'A aula já foi finalizada', HttpCode.WARNING
    elif match.IdTeam is None:
        return 'Aula não encontrada', HttpCode.WARNING
    
    memberUserIds = [member.IdUser for member in match.Team.Members if member.Refused == False and member.WaitingApproval == False]
    if user.IdUser not in memberUserIds:
        return 'Você não está nessa turma. Entre na turma para poder participar da aula', HttpCode.WARNING

    matchMember = db.session.query(MatchMember).filter((MatchMember.IdMatch == idMatch) & (MatchMember.IdUser == user.IdUser)).first()
    if matchMember is None:
        newMatchMember = MatchMember(
            IdUser = user.IdUser,
            IsMatchCreator = False,
            WaitingApproval = False,
            Refused = False,
            IdMatch = idMatch,
            EntryDate = datetime.now(),
            Quit = False,
            HasPaid = False,
        )
        db.session.add(newMatchMember)

    else:
        matchMember.IdUser = user.IdUser
        matchMember.IsMatchCreator = False
        matchMember.WaitingApproval = False
        matchMember.Refused = False
        matchMember.IdMatch = idMatch
        matchMember.EntryDate = datetime.now()
        matchMember.Quit = False
        matchMember.HasPaid = False
    
    for member in match.Members:
        if member.IsMatchCreator == True:
            teacher = member.User 

    newNotificationUser = NotificationUser(
        IdUser = teacher.IdUser,
        IdUserReplaceText = user.IdUser,
        IdMatch = idMatch,
        IdNotificationUserCategory = 10,
        Seen = False
    )
    db.session.add(newNotificationUser)
    db.session.commit()

    sendStudentConfirmedClassNotification(teacher, user, match)
    return "Sua presença foi confirmada!",HttpCode.ALERT

#Usuário solicita para cancelar a partida pelo app
@bp_match.route("/CancelMatch", methods=["POST"])
def CancelMatch():
    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idMatch = request.json.get('IdMatch')

    #Busca o usuário que solicitou o cancelamento
    user = User.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return 'Token inválido', HttpCode.WARNING

    #Busca a partida que será cancelada
    match = Match.query.get(idMatch) 
    if match is None:
        return 'Partida não encontrada', HttpCode.WARNING
    if match.IsFinished():
         return 'A partida já foi finalizada', HttpCode.WARNING
    
    #Se for uma partida válida
    if match.IsPaymentConfirmed and match.AsaasBillingType != "PAY_IN_STORE":

        #Gera o cupom de desconto
        #Gerar o código primeiro
        couponCode = generateRandomCouponCode(6)

        newCoupon = Coupon(
            DiscountType = "FIXED",
            Value = match.CostUser,
            Code = couponCode,
            IsValid = True,
            IdStoreValid = match.StoreCourt.IdStore,
            IdTimeBeginValid = 1,
            IdTimeEndValid = 24,
            DateCreated= datetime.now(),
            DateBeginValid = datetime.now(),
            DateEndValid = datetime.now() + timedelta(days=365),
            IsUniqueUse = True,
        )
        db.session.add(newCoupon)
        db.session.commit()

        #Envia o cupom de desconto por e-mail ao jogador
        emailUserReceiveCoupon(user.Email, newCoupon)

        match.AsaasPaymentStatus = "REFUNDED"

    match.Canceled = True

    #Exclui os jogadores da partida
    matchMembers = MatchMember.query.filter(MatchMember.IdMatch == idMatch)\
                            .filter(MatchMember.WaitingApproval == False)\
                            .filter(MatchMember.Refused == False)\
                            .filter(MatchMember.Quit == False).all()
    for matchMember in matchMembers:
        if matchMember.IsMatchCreator == True:
            #Envia notificação para a loja
            idNotificationUserCategory = 6
            newNotificationStore = NotificationStore(
                IdUser = matchMember.IdUser,
                IdStore = match.StoreCourt.IdStore,
                IdMatch = idMatch,
                IdNotificationStoreCategory = 2,
                EventDatetime = datetime.now()
            )
            db.session.add(newNotificationStore)
        else:
            if match.IsClass:
                idNotificationUserCategory = 12
            else:
                idNotificationUserCategory = 7
        if matchMember.Refused == False:
            #Envia notificação para os jogadores que haviam entrado na partida
            newNotificationUser = NotificationUser(
                IdUser = matchMember.IdUser,
                IdUserReplaceText = match.matchCreator().IdUser,
                IdMatch = idMatch,
                IdNotificationUserCategory = idNotificationUserCategory,
                Seen = False
            )
            db.session.add(newNotificationUser)
    if match.IsClass:
        sendClassCanceledByTeacher(match)
    else:
        sendMatchCanceledFromCreatorNotification(match)

    #Envia e-mail para a quadra avisando sobre o cancelamento
    emailStoreMatchCanceled(match)

    db.session.commit()
    return "Partida cancelada",HttpCode.ALERT

#Loja cancela o horário de um jogador
@bp_match.route("/CancelMatchEmployee", methods=["POST"])
def CancelMatchEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    idMatchReq = request.json.get('IdMatch')
    cancelationReasonReq = request.json.get('CancelationReason')

    #Busca a loja a partir do token do employee
    storeCourt = db.session.query(StoreCourt)\
            .join(Employee, Employee.IdStore == StoreCourt.IdStore)\
            .filter(or_(Employee.AccessToken == accessTokenReq, Employee.AccessTokenApp == accessTokenReq)).first()
    
    #Caso não encontrar Token
    if storeCourt is None:
        return webResponse("Token não encontrado", None), HttpCode.EXPIRED_TOKEN

    match = Match.query.get(idMatchReq)
    if match is None:
        return 'Partida não encontrada', HttpCode.WARNING
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (match.IsFinished())):
         return 'A partida já foi finalizada', HttpCode.WARNING
    else:
        
        if match.IsPaymentConfirmed and match.AsaasBillingType != "PAY_IN_STORE":
            valueToRefund = float(match.CostUser)
            responseRefund = refundPayment(paymentId= match.AsaasPaymentId, cost= valueToRefund, description= f"Partida cancelada pelo estabelecimento/IdMatch {match.IdMatch}")
            if responseRefund.status_code != 200:
                return "Não conseguimos processar o estorno. Tente novamente", HttpCode.WARNING
            match.AsaasPaymentStatus = "REFUNDED"

        match.Canceled = True
        match.BlockedReason = cancelationReasonReq

        matchMembers = MatchMember.query.filter(MatchMember.IdMatch == idMatchReq)\
                        .filter(MatchMember.WaitingApproval == False)\
                        .filter(MatchMember.Refused == False)\
                        .filter(MatchMember.Quit == False).all()
        for matchMember in matchMembers:

            newNotificationUser = NotificationUser(
                IdUser = matchMember.IdUser,
                IdUserReplaceText = matchMember.IdUser,
                IdMatch = idMatchReq,
                IdNotificationUserCategory = 9,
                Seen = False
            )
            db.session.add(newNotificationUser)

        db.session.commit()

        matchDatetime = datetime(match.Date.year, match.Date.month, match.Date.day)

        startDate = lastSundayOnLastMonth(matchDatetime)
        endDate = firstSundayOnNextMonth(matchDatetime)

        courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == storeCourt.IdStore).all()

        matches = queryMatchesForCourts([court.IdStoreCourt for court in courts], startDate, endDate)

        
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
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (match.IsFinished())):
         return 'A partida já foi finalizada', HttpCode.WARNING
    else:

        matchMember = MatchMember.query.filter((MatchMember.IdMatch == idMatch) & (MatchMember.IdUser == idUserDelete)).first()
        matchCreator = MatchMember.query.filter((MatchMember.IdMatch == idMatch) & (MatchMember.IsMatchCreator == True)).first()

        matchMember.Refused = True
        matchMember.Quit = True
        matchMember.WaitingApproval = False
        matchMember.QuitDate = datetime.now()
        matchMember.HasPaid = False

        newNotificationUser = NotificationUser(
            IdUser = idUserDelete,
            IdUserReplaceText = matchCreator.IdUser,
            IdMatch = idMatch,
            IdNotificationUserCategory = 5,
            Seen = False
        )
        db.session.add(newNotificationUser)

        db.session.commit()
        return "Jogador removido",HttpCode.ALERT

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

#Bloqueia um horário
@bp_match.route('/BlockHour', methods=['POST'])
def BlockHour():
    if not request.json:
        abort(400)

    accessTokenReq = request.json.get('AccessToken')
    idStoreCourtReq = request.json.get('IdStoreCourt')

    #Busca a loja a partir do token do employee
    storeCourt = getStoreCourtByToken(accessTokenReq, idStoreCourtReq)
    
    #Caso não encontrar Token
    if storeCourt is None:
        return webResponse("Token não encontrado", None), HttpCode.EXPIRED_TOKEN

    #Dia e horário 
    idHourReq = request.json.get('IdHour')
    dateReq = datetime.strptime(request.json.get('Date'), '%d/%m/%Y')

    #Motivo e esporte bloqueado
    blockedReasonReq = request.json.get('BlockedReason')
    idSportReq = request.json.get('IdSport')
    idUserReq = request.json.get('IdUser')
    idStorePlayerReq = request.json.get('IdStorePlayer')
    priceReq = request.json.get('Price')
    
    
    #Verifica se já tem uma partida agendada no mesmo horário
    concurrentMatch = queryConcurrentMatches([idStoreCourtReq],[dateReq], idHourReq, idHourReq+1)
    concurrentRecurrentMatches = queryConcurrentRecurrentMatches([idStoreCourtReq], [dateReq], idHourReq, idHourReq+1)

    if isHourAvailableForMatch(concurrentMatch, concurrentRecurrentMatches, idStoreCourtReq, dateReq, idHourReq):
        newMatch = Match(
            IdStoreCourt = idStoreCourtReq,
            IdSport = idSportReq,
            Date = dateReq,
            IdTimeBegin = idHourReq,
            IdTimeEnd = idHourReq+1,
            Cost = priceReq,
            CostUser = priceReq,
            CostDiscount = 0,
            OpenUsers = False,
            MaxUsers = 0,
            Canceled = False,
            CreationDate = datetime.now(),
            CreatorNotes = "",
            IdRecurrentMatch = 0,
            Blocked = True,
            BlockedReason = blockedReasonReq,
            AsaasBillingType = "BLOCKED",
            AsaasPaymentStatus = "CONFIRMED",
            CostFinal = priceReq,
            CostAsaasTax = 0,
            CostSandfriendsNetTax = 0,
            AsaasSplit = 0
        )
        db.session.add(newMatch)
        db.session.commit()
        
        newMatchMember = matchMember = MatchMember(
            IdUser = idUserReq,
            IsMatchCreator = True,
            WaitingApproval = False,
            Refused = False,
            IdMatch = newMatch.IdMatch,
            Quit = False,
            EntryDate = datetime.now(),
            IdStorePlayer = idStorePlayerReq,
            HasPaid = False,
        )
        db.session.add(newMatchMember)
        db.session.commit()

    else:
        return webResponse("Ops", "Não foi possível bloquear o horário. Uma partida já foi ou está sendo marcada"), HttpCode.WARNING

    db.session.commit()

    #Monta a lista de partidas que terá no mês para atualizar o calendário
    #Dias do mês
    startDate = lastSundayOnLastMonth(dateReq)
    endDate = firstSundayOnNextMonth(dateReq)

    courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == storeCourt.IdStore).all()

    #Retorna a lista de partidas
    matches = queryMatchesForCourts([court.IdStoreCourt for court in courts], startDate, endDate)
    
    matchList = []
    for match in matches:
        matchList.append(match.to_json_min())

    return jsonify({"Matches": matchList}), HttpCode.SUCCESS

#Desbloqueia um horário
@bp_match.route('/UnblockHour', methods=['POST'])
def UnblockHour():
    if not request.json:
        abort(400)

    accessTokenReq = request.json.get('AccessToken')
    idStoreCourtReq = request.json.get('IdStoreCourt')
    #Busca a loja a partir do token do employee
    storeCourt = getStoreCourtByToken(accessTokenReq, idStoreCourtReq)
    
    #Caso não encontrar Token
    if storeCourt is None:
        return webResponse("Token não encontrado", None), HttpCode.EXPIRED_TOKEN

    #Dia e horário 
    idHourReq = request.json.get('IdHour')
    dateReq = datetime.strptime(request.json.get('Date'), '%d/%m/%Y')

    match = db.session.query(Match)\
            .filter(Match.IdStoreCourt == idStoreCourtReq)\
            .filter(Match.Date == dateReq)\
            .filter(Match.IdTimeBegin == idHourReq)\
            .filter(Match.Blocked == True)\
            .first()

    #Verifica se existe uma partida "Blocked" no horário
    if match is not None:
        #apaga os membros da partida
        for member in match.Members:
            db.session.delete(member)
        #Deleta o match que está como "Blocked"
        db.session.delete(match)
    
    #Caso não tenha partida, verifica se existe um bloqueio mensalista nesse horário
    else:
        recurrentMatch = db.session.query(RecurrentMatch)\
            .filter(RecurrentMatch.Blocked == 1)\
            .filter(RecurrentMatch.Weekday == dateReq.weekday())\
            .filter((RecurrentMatch.IdTimeBegin == idHourReq) | ((RecurrentMatch.IdTimeBegin < idHourReq) & (RecurrentMatch.IdTimeEnd > idHourReq)))\
            .filter(RecurrentMatch.IdStoreCourt == idStoreCourtReq).first()

        #Se existir um bloqueio mensalista, cria uma partida como "Cancelled" - Frontend vai entender que uma partida foi cancelada e o horário liberou
        if recurrentMatch is not None:
            newMatch = Match(
                IdStoreCourt = idStoreCourtReq,
                IdSport = recurrentMatch.IdSport,
                Date = dateReq,
                IdTimeBegin = idHourReq,
                IdTimeEnd = idHourReq+1,
                Cost = 0,
                CostUser = 0,
                CostDiscount = 0,
                OpenUsers = False,
                MaxUsers = 0,
                Canceled = True,
                CreationDate = datetime.now(),
                CreatorNotes = "",
                IdRecurrentMatch = recurrentMatch.IdRecurrentMatch,
                Blocked = 0,
                BlockedReason = "",
                AsaasBillingType = "UNBLOCKED",
                AsaasPaymentStatus = "CONFIRMED",
                CostFinal = 0,
                CostAsaasTax = 0,
                CostSandfriendsNetTax = 0,
                AsaasSplit = 0
            )
            db.session.add(newMatch)
    
    db.session.commit()

    #Monta a lista de partidas que terá no mês para atualizar o calendário
    #Dias do mês
    startDate = lastSundayOnLastMonth(dateReq)
    endDate = firstSundayOnNextMonth(dateReq)

    courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == storeCourt.IdStore).all()

    #Retorna a lista de partidas
    matches = queryMatchesForCourts([court.IdStoreCourt for court in courts], startDate, endDate)
    
    matchList = []
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

    employee = getEmployeeByToken(accessTokenReq)

    if employee is None:
        return '1', HttpCode.EXPIRED_TOKEN
    
    matches =  db.session.query(Match)\
                    .filter(Match.IdStoreCourt.in_([court.IdStoreCourt for court in employee.Store.Courts]))\
                    .filter((Match.Date >= dateStartReq) & (Match.Date <= dateEndReq))\
                    .filter((Match.Canceled == False) | ((Match.Canceled == True) & (Match.IsFromRecurrentMatch)))\
                    .filter(Match.Blocked != True).all()
    
    matchList = []
    for match in matches:
        matchList.append(match.to_json_min())
    return {'Matches': matchList}, HttpCode.SUCCESS

@bp_match.route('/UpdateClassMatchMembers', methods=['POST'])
def UpdateClassMatchMembers():

    if not request.json:
        abort(HttpCode.ABORT)

    accessToken = request.json.get('AccessToken')
    idMatch = request.json.get('IdMatch')
    usersToAdd = request.json.get('UsersToAdd')
    usersToRemove = request.json.get('UsersToRemove')

    user = User.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return 'Token inválido', HttpCode.WARNING

    match = Match.query.get(idMatch)
    if match is None:
        return 'Partida não encontrada', HttpCode.WARNING

    for member in match.Members:
        print("1")
        print(member.User.FirstName)
        if member.IdUser in usersToRemove:
            print("FOUND")
            member.Quit = True
            member.QuitDate = datetime.now()
            member.Cost = None
            member.HasPaid = False
        elif member.IdUser in usersToAdd:
            member.Quit = False
            member.QuitDate = None
            usersToAdd.remove(member.IdUser)

    for idUser in usersToAdd:
        print("2")
        print(idUser)
        newMember = MatchMember(
            IdMatch = idMatch,
            IdUser = idUser,
            IsMatchCreator = False,
            WaitingApproval = False,
            Refused = False,
            Quit = False,
            HasPaid = False,
        )
        db.session.add(newMember)

    db.session.commit()
    print("will return")
    return 'Sua aula foi alterada', HttpCode.ALERT

#Gera lista de partidas no mesmo horário selecionado
def queryConcurrentMatches(listIdStoreCourt, listDate, timeStart, timeEnd):
    matches = db.session.query(Match)\
            .filter(Match.IdStoreCourt.in_(listIdStoreCourt))\
            .filter(Match.Date.in_(listDate))\
            .filter((Match.Canceled == False) | ((Match.Canceled == True) & (Match.IdRecurrentMatch != 0)))\
            .filter(((Match.IdTimeBegin >= timeStart) & (Match.IdTimeBegin < timeEnd)) | \
                    ((Match.IdTimeEnd > timeStart) & (Match.IdTimeEnd <= timeEnd)) | \
                    ((Match.IdTimeBegin < timeStart) & (Match.IdTimeEnd > timeStart))).all()
    
    return [match for match in matches if match.IsFinished() ==  False and match.isPaymentExpired == False]

#Gera lista de mensalistas no mesmo horário selecionado
def queryConcurrentRecurrentMatches(listIdStoreCourt, weekdays, timeStart, timeEnd):
    recurrentMatches = db.session.query(RecurrentMatch)\
                    .filter(RecurrentMatch.IdStoreCourt.in_(listIdStoreCourt))\
                    .filter(RecurrentMatch.Weekday.in_(weekdays))\
                    .filter(RecurrentMatch.Canceled == False)\
                    .filter(RecurrentMatch.IsExpired == False)\
                    .filter(((RecurrentMatch.IdTimeBegin >= timeStart) & (RecurrentMatch.IdTimeBegin < timeEnd)) | \
                            ((RecurrentMatch.IdTimeEnd > timeStart) & (RecurrentMatch.IdTimeEnd <= timeEnd)) | \
                            ((RecurrentMatch.IdTimeBegin < timeStart) & (RecurrentMatch.IdTimeEnd > timeStart))).all()
                            
    return recurrentMatches


def isHourAvailableForMatch(matches, recurrentMatches, idStoreCourt, date, hour):
    #Verifica se não tem nenhuma partida no mesmo horario, dia e quadra
    if len([match for match in matches if \
                (match.IdStoreCourt ==  idStoreCourt) and \
                (match.Canceled == False) and \
                (match.Date == date) and \
                ((match.IdTimeBegin == hour) or \
                ((match.IdTimeBegin < hour) and (match.IdTimeEnd > hour)))\
        ]) > 0:
        return False
    else:
        concurrentRecurrentMatch = [recurrentMatch for recurrentMatch in recurrentMatches if \
                    (recurrentMatch.IdStoreCourt ==  idStoreCourt) and \
                    (recurrentMatch.Weekday == date.weekday()) and \
                    ((recurrentMatch.IdTimeBegin == hour) or \
                        ((recurrentMatch.IdTimeBegin < hour) and (recurrentMatch.IdTimeEnd > hour)))\
        ]
        if len(concurrentRecurrentMatch) == 0:
            return True
        
        #na teoria, se tem um concurrentRecurrentMatch deveria ter 1 ocorrencia só, mas como ele é uma lista fiz o for loop
        for recurrentMatch in concurrentRecurrentMatch:
            #caso tenha um mensalista q foi bloqueado pela quadra. 
            #Esse caso tem q cuidar porque a quadra pode cancelar uma partida avulsa desse mensalista
            if recurrentMatch.Blocked == False:
                if date >= recurrentMatch.ValidUntil.date():
                    return False
            
            if len([match for match in matches if \
                (match.IdStoreCourt ==  idStoreCourt) and \
                (match.Canceled == True) and \
                (match.IdRecurrentMatch == recurrentMatch.IdRecurrentMatch) and \
                (match.Date == date) and \
                ((match.IdTimeBegin == hour) or \
                ((match.IdTimeBegin < hour) and (match.IdTimeEnd > hour)))\
            ]) > 0:
                #Quer dizer q o horário é de um mensalista, mas nesse dia foi cancelado
                return True
            else:
                return False
           

