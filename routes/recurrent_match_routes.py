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
from ..Models.notification_store_model import NotificationStore
from ..emails import emailUserMatchConfirmed, emailUserRecurrentMatchConfirmed
from ..routes.match_routes import queryConcurrentMatches
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

#Retorna uma string com o horário (ex: 9 -> 09:00)
def getHourString(hourIndex):
    #zfill - adiciona 0 no início se preciso
    return f"{str(hourIndex).zfill(2)}:00"#GAMBIARRA

#A princípio não é utilizado - Comentei para ver se podemos excluir (23/10/2023)
# @bp_recurrent_match.route('/UserRecurrentMatches', methods=['POST'])
# def UserRecurrentMatches():
    
#     accessToken = request.json.get('AccessToken')

#     user = User.query.filter_by(AccessToken = accessToken).first()

#     if user is None:
#         return '1', HttpCode.EXPIRED_TOKEN

    
#     recurrentMatches = db.session.query(RecurrentMatch)\
#                         .filter(RecurrentMatch.IdUser == user.IdUser)\
#                         .filter(RecurrentMatch.Canceled == False)\
#                         .filter( RecurrentMatch.ValidUntil > datetime.now()).all()

#     if recurrentMatches is None:
#         return "nada", 200
    
#     recurrentMatchesList =[]
#     for recurrentMatch in recurrentMatches:
#         recurrentMatchesList.append(recurrentMatch.to_json())
    
#     return jsonify({'RecurrentMatches': recurrentMatchesList}), HttpCode.SUCCESS


#Busca horários mensalistas disponíveis - na área do mensalista
@bp_recurrent_match.route("/SearchRecurrentCourts", methods=["POST"])
def SearchRecurrentCourts():
    if not request.json:
        abort(HttpCode.ABORT)
    
    #Recebidos da busca do app
    accessToken = request.json.get('AccessToken')
    sportId = int(request.json.get('IdSport'))
    cityId = request.json.get('IdCity')
    days = request.json.get('Days').split(";")
    timeStart = request.json.get('TimeStart')
    timeEnd = request.json.get('TimeEnd')

    #Verifica se o usuário é válido
    user = User.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return 'Token inválido - Realize login novamente', HttpCode.EXPIRED_TOKEN

    #Estabelecimentos na cidade e validados/aprovados
    stores = db.session.query(Store).filter(Store.IdCity == cityId)\
                                    .filter(Store.IdStore.in_([store.IdStore for store in getAvailableStores()])).all()

    #Quadras disponíveis
    #Unir tabela de quadras e a tabela com os esportes de cada quadra
    #Filtra as quadras que possuem o esporte escolhido
    courts = db.session.query(StoreCourt)\
                    .join(StoreCourtSport, StoreCourtSport.IdStoreCourt == StoreCourt.IdStoreCourt)\
                    .join(Store, Store.IdStore == StoreCourt.IdStore)\
                    .filter(Store.IdCity == cityId)\
                    .filter(StoreCourtSport.IdSport == sportId)\
                    .filter(StoreCourt.IdStore.in_(store.IdStore for store in stores)).all()

    #Destas quadras, os horários e preços disponíveis
    courtHours = db.session.query(StorePrice)\
                    .filter(StorePrice.IdStoreCourt.in_(court.IdStoreCourt for court in courts)).all()
    
    #Partidas mensalistas já existente nas quadras buscadas, que ainda não estão expiradas
    recurrentMatches = db.session.query(RecurrentMatch)\
                        .filter(RecurrentMatch.Canceled == False)\
                        .filter(RecurrentMatch.IdStoreCourt.in_(court.IdStoreCourt for court in courts))\
                        .filter(RecurrentMatch.ValidUntil > datetime.now()).all()

    #Rever, a princípio não faz nada, pois já é verificado na linha acima (ValidUntil)
    recurrentMatches = [recurrentMatch for recurrentMatch in recurrentMatches if recurrentMatch.isPaymentExpired == False]

    dayList = []
    IdStoresList = []
    #Verifica os dias da semana em que o jogador buscou
    for day in days:
        jsonStores = []
        #Para cada estabelecimento disponível
        for store in stores:
            #Pega as quadras que essa loja possui
            filteredCourts = [court for court in courts if court.IdStore == store.IdStore]

            if(len(filteredCourts) > 0):
                #Horários de operação do estabelecimento
                #Considera os horários de funcionamento da primeira quadra do estabelecimento (pois todas as quadras devem possuir o mesmo horário de funcionamento)
                #Horário de operação apenas no dia do loop
                #Horários do range que o jogador selecionou
                storeOperationHours = [storeOperationHour for storeOperationHour in courtHours if \
                                    (storeOperationHour.IdStoreCourt == filteredCourts[0].IdStoreCourt) and\
                                    (storeOperationHour.Weekday == int(day)) and \
                                    ((storeOperationHour.IdAvailableHour >= getHourIndex(timeStart)) and (storeOperationHour.IdAvailableHour < getHourIndex(timeEnd)))]

                jsonStoreOperationHours =[]
                #Montar o json que ele vai retornar para o app
                for storeOperationHour in storeOperationHours:
                    jsonAvailableCourts =[]
                    #Para cada horário de operação da quadra
                    for filteredCourt in filteredCourts:
                        #Para cada quadra disponível nesse horário
                        #Gera uma lista de partidas mensalistas que já existem nesta quadra neste horário
                        #Partida existe ele verifica:
                            #Horário de inicio == horário do loop 
                            #Horário de início < horário do loop AND horário de fim > horário do loop
                            #match.IdStoreCourt
                        concurrentMatch = [match for match in recurrentMatches if \
                                    (match.IdStoreCourt ==  filteredCourt.IdStoreCourt) and \
                                    (match.Weekday == int(day)) and \
                                    ((match.IdTimeBegin == storeOperationHour.IdAvailableHour) or ((match.IdTimeBegin < storeOperationHour.IdAvailableHour) and (match.IdTimeEnd > storeOperationHour.IdAvailableHour)))\
                                    ]

                        #Caso não exista partidas conflitantes            
                        if len(concurrentMatch) == 0:
                            #Pega o horário e preço se
                            #
                            recurrentCourtHour = [courtHour for courtHour in courtHours if \
                                    (courtHour.IdStoreCourt == filteredCourt.IdStoreCourt) and \
                                    (courtHour.Weekday == int(day)) and \
                                    (courtHour.IdAvailableHour == storeOperationHour.IdAvailableHour)\
                                    ][0]
                            #Se naõ tiver preço, quer dizer que o estabelecimento não aceita horário mensalista neste dia nesta quadra
                            if recurrentCourtHour.RecurrentPrice is not None:
                                #Adiciona no json o horário e preço que está disponível para mensalista
                                jsonAvailableCourts.append({
                                    'IdStoreCourt':filteredCourt.IdStoreCourt,
                                    'Price': int(recurrentCourtHour.RecurrentPrice)
                                })

                    if jsonAvailableCourts:
                        #Adiciona no json o horário dos preços que foram adicionados acima
                        jsonStoreOperationHours.append({
                            'Courts': jsonAvailableCourts, 
                            'TimeBegin':storeOperationHour.AvailableHour.HourString,
                            'TimeFinish':getHourString(storeOperationHour.IdAvailableHour + 1),
                            'TimeInteger': storeOperationHour.IdAvailableHour
                        })
                
                #Depois de verificar todos os horários
                #Adiciona o horário de operação de cada quadra
                if jsonStoreOperationHours:
                    jsonStores.append({
                        'IdStore':store.IdStore, 
                        'Hours':jsonStoreOperationHours
                    })
                    #Gera a lista de quadras, para não repetir a loja
                    if store.IdStore not in IdStoresList:
                        IdStoresList.append(store.IdStore)

        #Horários e preços dos agendamentos disponíveis de cada quadra
        if jsonStores:
            dayList.append({
                'Date':day, 
                'Stores':jsonStores
                })

    jsonCompleto = jsonify({
        #Horários e preços dos agendamentos disponíveis
        'Dates':dayList, 
        #Informações da quadra
        'Stores': [store.to_json() for store in stores]
        })

    return jsonCompleto, HttpCode.SUCCESS

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
        cvvReq = request.json.get("Cvv")

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
    
    concurrentMatches = queryConcurrentMatches([int(idStoreCourtReq)], daysList, timeStartReq, timeEndReq)

    if len(concurrentMatches) > 0 :
        return "Ops, um dos horários não está mais disponível. Pesquise novamente", HttpCode.WARNING
    
    if len(daysList) == 0:
        return "Ops, esse mensalista não tem horários livres nesse mês. Pesquise outro horário", HttpCode.WARNING

    asaasPaymentId = None
    asaasBillingType = None
    asaasPaymentStatus = None
    asaasPixCode = None
    costFinalReq = None
    costAsaasTaxReq = None
    costSandfriendsNetTaxReq = None
    asaasSplitReq = None

    #busca a quadra que vai ser feita a cobrança
    store = db.session.query(Store)\
            .join(StoreCourt, StoreCourt.IdStore == Store.IdStore)\
            .filter(StoreCourt.IdStoreCourt == idStoreCourtReq).first()
    
    now = datetime.now()

    #### PIX
    if paymentReq == 1:
        #Atualiza o CPF caso não tenha
        if cpfReq != user.Cpf:
            user.Cpf = cpfReq
            db.session.commit()
            responseCpf = updateCpf(user)

            if responseCpf.status_code != 200:
                return "Ops, verifique se seu CPF está correto.", HttpCode.WARNING

        #Gera a cobrança no Asaas
        responsePayment = createPaymentPix(
            user= user, 
            value= totalCostReq,
            store= store,
        )
        if responsePayment.status_code != 200:
            return "Não foi possível processar seu pagamento. Tente novamente", HttpCode.WARNING

        #Obtém o código para pagemento do Pix
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
        costReq = responsePayment.json().get('value')
        costAsaasTaxReq = costReq - costNetReq
        #Valor da remuneração do Sandfriends
        costSandfriendsNetTaxReq = costReq - costAsaasTaxReq - costFinalReq
        #Porcentagem do Split
        asaasSplitReq = responsePayment.json().get('split')[0].get('percentualValue')

        validUntil = now + timedelta(minutes = 30)

    #### CARTÃO DE CRÉDITO
    elif paymentReq == 2:
        creditCard = db.session.query(UserCreditCard).filter(UserCreditCard.IdUserCreditCard == idCreditCardReq).first()

        if creditCard is None:
            return "Não foi possível processar seu pagamento. Tente novamente", HttpCode.WARNING
        
        #Gera a cobrança no Asaas
        responsePayment = createPaymentCreditCard(
            user= user, 
            creditCard= creditCard,
            value= totalCostReq,
            store= store,
            cvv= cvvReq,
        )
        
        if responsePayment.status_code != 200:
            return "Não foi possível processar seu pagamento. Tente novamente", HttpCode.WARNING

        #Dados que retornam do Asaas
        asaasPaymentId = responsePayment.json().get('id')
        asaasBillingType = responsePayment.json().get('billingType')
        asaasPaymentStatus = "PENDING"
        #Valor final, após Split - o que a quadra irá receber
        costFinalReq = responsePayment.json().get('split')[0].get('totalValue')
        #Valor da taxa do Asaas
        costNetReq = responsePayment.json().get('netValue')
        costReq = responsePayment.json().get('value')
        costAsaasTaxReq = costReq - costNetReq
        #Valor da remuneração do Sandfriends
        costSandfriendsNetTaxReq = costReq - costAsaasTaxReq - costFinalReq
        #Porcentagem do Split
        asaasSplitReq = responsePayment.json().get('split')[0].get('percentualValue')

        validUntil = now + timedelta(minutes = 30)

    #### PAGAMENTO NO LOCAL
    elif paymentReq == 3:
        asaasBillingType = "PAY_IN_STORE"
        asaasPaymentStatus = "CONFIRMED"

        costFinalReq = costReq
        costAsaasTaxReq = 0
        costSandfriendsNetTaxReq = 0
        asaasSplitReq = costReq

        if isRenovatingReq:
            validUntil = getLastDayOfMonth(datetime(now.year, now.month+1, 1))
        else:
            validUntil = getLastDayOfMonth(now)

    else:
        return "Forma de pagamento inválida", HttpCode.WARNING

    recurrentMatchId = None
        
    if isRenovatingReq:
        recurrentMatch = db.session.query(RecurrentMatch)\
            .filter(RecurrentMatch.IdStoreCourt == int(idStoreCourtReq)) \
            .filter(RecurrentMatch.Weekday == weekDayReq) \
            .filter(RecurrentMatch.Canceled == False)\
            .filter((RecurrentMatch.IdTimeBegin == timeStartReq) & (RecurrentMatch.IdTimeEnd == timeEndReq)).first()
       
        recurrentMatch.LastPaymentDate = now.date()
        recurrentMatch.ValidUntil = validUntil
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
            ValidUntil = validUntil
        )
        db.session.add(newRecurrentMatch)
        db.session.commit()
        db.session.refresh(newRecurrentMatch)
        recurrentMatchId = newRecurrentMatch.IdRecurrentMatch
    
    matchToNotify = None

    #Cria as partidas na tabela Match
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
            CostFinal = costFinalReq,
            CostAsaasTax = costAsaasTaxReq,
            CostSandfriendsNetTax = costSandfriendsNetTaxReq,
            AsaasSplit = asaasSplitReq
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

        if matchToNotify is None:
            matchToNotify = newMatch
    
    #Se for pagamento no local, já envia notificação pra quadra sobre o agendamento
    if paymentReq == 3:
        if isRenovatingReq:
            idNotification = 4
        else:
            idNotification = 3
        #Notificação para a loja
        newNotificationStore = NotificationStore(
            IdUser = user.IdUser,
            IdStore = store.IdStore,
            IdMatch = matchToNotify.IdMatch,
            IdNotificationStoreCategory = idNotification,
            EventDatetime = datetime.now()
        )
        db.session.add(newNotificationStore)
        db.session.commit()
        emailUserRecurrentMatchConfirmed(matchToNotify)

    #PIX
    if paymentReq == 1:
        return jsonify({'Message':"Seu horário mensalista foi reservado!", "Pixcode": asaasPixCode}), HttpCode.ALERT
    else:
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


    if (recurrentMatch is not None) and (isRenovating == False) and(recurrentMatch.isPaymentExpired == False):
        return "Ops, esse horário não está mais disponível", HttpCode.WARNING

    if isRenovating:
        nextMonth = datetime(datetime.today().year, datetime.today().month + 1, 1)
        daysList = [day for day in daterange( nextMonth.date(), getLastDayOfMonth(nextMonth)) if day.weekday() == weekDay]
    else:
        daysList = [day for day in daterange(datetime.today().date(), getLastDayOfMonth(datetime.now())) if day.weekday() == weekDay]
    
    matches = queryConcurrentMatches([int(idStoreCourt)], daysList, timeStart, timeEnd)

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
