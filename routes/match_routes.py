from flask import Blueprint, jsonify, abort, request, json
from datetime import datetime, timedelta, date
from sqlalchemy import func 
from ..extensions import db
import os
from ..responses import webResponse
from ..utils import firstSundayOnNextMonth, lastSundayOnLastMonth, isCurrentMonth
from ..routes.store_routes import getAvailableStores
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
from ..emails import emailUserMatchConfirmed
from ..Asaas.Customer.update_customer import updateCpf
from ..Asaas.Payment.create_payment import createPaymentPix, createPaymentCreditCard, getSplitPercentage
from ..Asaas.Payment.refund_payment import refundPayment
from ..Asaas.Payment.generate_qr_code import generateQrCode
from sandfriends_backend.push_notifications import sendMatchInvitationNotification, sendMatchInvitationRefusedNotification, sendMatchInvitationAcceptedNotification, sendMemberLeftMatchNotification, sendMatchCanceledFromCreatorNotification

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
                                    .filter(Store.IdStore.in_([store.IdStore for store in getAvailableStores()])).all()

    #query de todas as quadras(não estabelecimento) que aceita o esporte solicitado
    courts = db.session.query(StoreCourt)\
                    .join(StoreCourtSport, StoreCourtSport.IdStoreCourt == StoreCourt.IdStoreCourt)\
                    .filter(StoreCourtSport.IdSport == sportId)\
                    .filter(StoreCourt.IdStore.in_(store.IdStore for store in stores)).all()

    #busca os horarios de todas as quadras e seus respectivos preços
    courtHours = db.session.query(StorePrice)\
                    .filter(StorePrice.IdStoreCourt.in_(court.IdStoreCourt for court in courts)).all()
                    
    matches = queryConcurrentMatches([court.IdStoreCourt for court in courts], daterange(dateStart.date(), dateEnd.date()), timeStart, timeEnd)

    searchWeekdays= []
    for searchDay in daterange(dateStart.date(), dateEnd.date()):
        if(searchDay.weekday() not in searchWeekdays):
            searchWeekdays.append(searchDay.weekday())
    #lembrando que aqui são as partidas mensalistas e os horários bloqueados recorrentemente
    recurrentMatches = db.session.query(RecurrentMatch)\
                    .filter(RecurrentMatch.IdStoreCourt.in_(court.IdStoreCourt for court in courts))\
                    .filter(RecurrentMatch.Weekday.in_(searchWeekdays))\
                    .filter(RecurrentMatch.Canceled == False)\
                    .filter(((RecurrentMatch.IdTimeBegin >= timeStart) & (RecurrentMatch.IdTimeBegin < timeEnd)) | \
                            ((RecurrentMatch.IdTimeEnd > timeStart) & (RecurrentMatch.IdTimeEnd <= timeEnd)) | \
                            ((RecurrentMatch.IdTimeBegin < timeStart) & (RecurrentMatch.IdTimeEnd > timeStart))).all()

    #partidas abertas
    jsonOpenMatches = []
    for match in matches:
        if (match.OpenUsers == True) and (match.Canceled == False) and (match.IdSport == sportId):
            userAlreadyInMatch = False
            matchMemberCounter = 0
            for member in match.Members:
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
                        if(not concurrentMatch) and \
                            (not concurrentBlockedHour) and \
                            (not( not(isCurrentMonth(validDate)) and concurrentRecurrentMatch )):

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

    #Lembrando que aqui são as partidas mensalistas e os horários bloqueados recorrentemente
    concurrentRecurrentMatch = db.session.query(RecurrentMatch)\
                    .filter(RecurrentMatch.IdStoreCourt == int(idStoreCourtReq))\
                    .filter(RecurrentMatch.Weekday == dateReq.weekday())\
                    .filter(RecurrentMatch.Canceled == False)\
                    .filter(((RecurrentMatch.IdTimeBegin >= timeStartReq) & (RecurrentMatch.IdTimeBegin < timeEndReq))  | \
                ((RecurrentMatch.IdTimeEnd > timeStartReq) & (RecurrentMatch.IdTimeEnd <= timeEndReq))      | \
                ((RecurrentMatch.IdTimeBegin < timeStartReq) & (RecurrentMatch.IdTimeEnd > timeStartReq))   \
                ).all()
    concurrentRecurrentMatch = [recurrentMatch for recurrentMatch in concurrentRecurrentMatch if recurrentMatch.isPaymentExpired == False]

    #Caso o horário não esteja mais disponível na hora dele fazer a reserva
    if (len(concurrentMatch) > 0) or (len(concurrentRecurrentMatch) > 0):
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
                discountValue = coupon.Value

        costUser = float(costReq - discountValue)

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
                discountValue = coupon.Value

        costUser = float(costReq - discountValue)

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
        emailUserMatchConfirmed(newMatch)
    #PIX
    if paymentReq == 1:
        return jsonify({'Message':"Sua partida foi reservada!", "Pixcode": asaasPixCode}), HttpCode.ALERT
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

        for member in match.Members:
            if member.IsMatchCreator == True:
                newNotificationUser = NotificationUser(
                    IdUser = member.IdUser,
                    IdUserReplaceText = matchMember.IdUser,
                    IdMatch = idMatch,
                    IdNotificationUserCategory = 8,
                    Seen = False
                )
                db.session.add(newNotificationUser)
                break
        db.session.commit()

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
    elif (match.IsFinished()):
         return 'A partida já foi finalizada', HttpCode.WARNING
    else:

        if match.IsPaymentConfirmed and match.AsaasBillingType != "PAY_IN_STORE":
            responseRefund = refundPayment(paymentId= match.AsaasPaymentId, description= f"Partida cancelada/IdMatch {match.IdMatch}")
            if responseRefund.status_code != 200:
                return "Não conseguimos processar o estorno. Tente novamente", HttpCode.WARNING
            match.AsaasPaymentStatus = "REFUNDED"

        match.Canceled = True

        matchMembers = MatchMember.query.filter(MatchMember.IdMatch == idMatch)\
                                .filter(MatchMember.WaitingApproval == False)\
                                .filter(MatchMember.Refused == False)\
                                .filter(MatchMember.Quit == False).all()
        for matchMember in matchMembers:
            matchMember.Quit=True
            matchMember.QuitDate=datetime.now()
            if matchMember.IsMatchCreator == True:
                idNotificationUserCategory = 6
                #notificação para a loja
                newNotificationStore = NotificationStore(
                    IdUser = matchMember.IdUser,
                    IdStore = match.StoreCourt.IdStore,
                    IdMatch = idMatch,
                    IdNotificationStoreCategory = 2,
                    EventDatetime = datetime.now()
                )
                db.session.add(newNotificationStore)
            else:
                idNotificationUserCategory = 7
            if matchMember.Refused == False:
                newNotificationUser = NotificationUser(
                    IdUser = matchMember.IdUser,
                    IdUserReplaceText = match.matchCreator().IdUser,
                    IdMatch = idMatch,
                    IdNotificationUserCategory = idNotificationUserCategory,
                    Seen = False
                )
                db.session.add(newNotificationUser)
                sendMatchCanceledFromCreatorNotification(match.matchCreator().User,matchMember.User, match)
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
            responseRefund = refundPayment(paymentId= match.AsaasPaymentId, description= f"Partida cancelada pelo estabelecimento/IdMatch {match.IdMatch}")
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
            matchMember.Quit=True
            matchMember.QuitDate=datetime.now()

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
    elif (match.Date < datetime.today().date()) or((match.Date == datetime.today().date()) and (match.IsFinished())):
         return 'A partida já foi finalizada', HttpCode.WARNING
    else:

        matchMember = MatchMember.query.filter((MatchMember.IdMatch == idMatch) & (MatchMember.IdUser == idUserDelete)).first()
        matchCreator = MatchMember.query.filter((MatchMember.IdMatch == idMatch) & (MatchMember.IsMatchCreator == True)).first()

        matchMember.Refused = True
        matchMember.Quit = True
        matchMember.WaitingApproval = False
        matchMember.QuitDate = datetime.now()
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


@bp_match.route('/BlockUnblockHour', methods=['POST'])
def BlockUnblockHour():
    if not request.json:
        abort(400)

    accessTokenReq = request.json.get('AccessToken')
    idStoreCourtReq = request.json.get('IdStoreCourt')

    #busca a loja a partir do token do employee
    storeCourt = getStoreCourtByToken(accessTokenReq, idStoreCourtReq)
    
    #Caso não encontrar Token
    if storeCourt is None:
        return webResponse("Token não encontrado", None), HttpCode.EXPIRED_TOKEN

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
            IdRecurrentMatch = 0,
            Blocked = blockedReq,
            BlockedReason = blockedReasonReq,
            AsaasBillingType = "BLOCKED",
            AsaasPaymentStatus = "BLOCKED",
            CostFinal = 0,
            CostAsaasTax = 0,
            CostSandfriendsNetTax = 0,
            AsaasSplit = 0
        )
        db.session.add(newMatch)

    else:
        #se tinha alguma partida com custo != 0 quer dizer q alguem agendou uma partida nesse meio tempo, ai não pode mais bloear o horario
        if match.Cost != 0:
            return webResponse("Ops", "Não foi possível bloquear o horário. Uma partida já foi ou está sendo marcada"), HttpCode.WARNING
        
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

    employee = getEmployeeByToken(accessTokenReq)

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

#Gera lista de partidas no mesmo horário selecionado
def queryConcurrentMatches(listIdStoreCourt, listDate, timeStart, timeEnd):
    matches = db.session.query(Match)\
            .filter(Match.IdStoreCourt.in_(listIdStoreCourt))\
            .filter(Match.Date.in_(listDate))\
            .filter(Match.Canceled == False) \
            .filter(((Match.IdTimeBegin >= timeStart) & (Match.IdTimeBegin < timeEnd)) | \
                    ((Match.IdTimeEnd > timeStart) & (Match.IdTimeEnd <= timeEnd)) | \
                    ((Match.IdTimeBegin < timeStart) & (Match.IdTimeEnd > timeStart))).all()
    
    return [match for match in matches if match.IsFinished() ==  False and match.isPaymentExpired == False]
