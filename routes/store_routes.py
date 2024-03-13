from flask import Blueprint, jsonify, abort, request
from flask_cors import cross_origin
from datetime import datetime, timedelta, date
from ..Models.store_model import Store
from ..extensions import db
from ..responses import webResponse
from ..Models.http_codes import HttpCode
from ..Models.city_model import City
from ..Models.state_model import State
from ..Models.store_photo_model import StorePhoto
from ..Models.store_price_model import StorePrice
from ..Models.sport_model import Sport
from ..Models.match_model import Match
from ..Models.employee_model import Employee
from ..Models.available_hour_model import AvailableHour
from ..Models.store_court_model import StoreCourt
from ..emails import emailStoreWelcomeConfirmation, emailStoreApproved, emailStoreAwaitingApproval
from ..access_token import EncodeToken, DecodeToken
from sqlalchemy import func
import base64
import bcrypt
import os

from ..Asaas.Account.create_account import createCustomer

bp_store = Blueprint('bp_store', __name__)

@bp_store.route('/AddStore', methods=['POST'])
def AddStore():
    if not request.json:
        abort(400)

    cityReq = request.json.get('City'),
    stateReq = request.json.get('State'),

    #primeiro recebe a cidade e o estado pra ver pegar o stateId e o cityId
    city = db.session.query(City).filter(func.lower(City.City) == func.lower(cityReq)).first()
    state = db.session.query(State).filter(func.lower(State.UF) == func.lower(stateReq)).first()

    #Verificações de Cidade e Estado
    if city is None:
        return webResponse("Cidade não encontrada", None), HttpCode.WARNING

    if state is None:
        return webResponse("Estado não encontrado", None), HttpCode.WARNING

    if city.IdState != state.IdState:
        return webResponse("Esta cidade não pertence a esse estado", None), HttpCode.WARNING

    #Cria o objeto store com os dados enviados pelo gestor da quadra
    #Já formata corretamente maiúsculas
    storeReq = Store(
        Name = request.json.get('Name'),
        Address = (request.json.get('Address')).title(),
        AddressNumber = (request.json.get('AddressNumber')).title(),
        IdCity = city.IdCity,
        PhoneNumber1 = request.json.get('PhoneStore'),    #Quadra
        PhoneNumber2 = request.json.get('PhoneOwner'),    #Pessoal
        CNPJ = request.json.get('CNPJ'),
        CEP = request.json.get('CEP'),
        Neighbourhood = (request.json.get('Neighbourhood')).title(),
        CPF = request.json.get('CPF'),
        RegistrationDate = datetime.now()
    )

    passwordReq = request.json.get('Password').encode('utf-8')

    #Employee que será criado automaticamente - o dono da quadra
    employeeReq = Employee(
        Email = (request.json.get('Email')).lower(),
        FirstName = (request.json.get('FirstName')).title(),
        LastName = (request.json.get('LastName')).title(),
        Password = bcrypt.hashpw(passwordReq, bcrypt.gensalt()),
        Admin = True,
        StoreOwner = True,
        RegistrationDate = datetime.now()
    ) 

    #Algum valor nulo que é exigido
    if storeReq.hasEmptyRequiredValues() or employeeReq.hasEmptyRequiredValues():
        return webResponse("Favor preencher todos os campos necessários", None), HttpCode.WARNING

    #Outra quadra com o mesmo nome
    nameQuery = db.session.query(Store).filter(func.lower(Store.Name) == func.lower(storeReq.Name)).first()
    if nameQuery is not None:
        return webResponse("Já existe um estabelecimento com este nome", "Favor escolher outro nome"), HttpCode.WARNING

    #Outra quadra com o mesmo email
    emailQuery = db.session.query(Employee).filter(Employee.Email == employeeReq.Email).first()
    if emailQuery is not None:
        return webResponse("Já existe um estabelecimento com este e-mail", None), HttpCode.WARNING

    #Outra quadra com o mesmo CNPJ - exceto se ele for nulo (sem CNPJ)
    if not (storeReq.CNPJ is None or storeReq.CNPJ == ""):
        cnpjQuery = db.session.query(Store).filter(Store.CNPJ == storeReq.CNPJ).first()
        if cnpjQuery is not None:
            return webResponse("Já existe um estabelecimento com este CNPJ", None), HttpCode.WARNING

    #Outra quadra no mesmo endereço
    addressQuery = db.session.query(Store).filter(\
        func.lower(Store.Address) == func.lower(storeReq.Address),\
        func.lower(Store.AddressNumber) == func.lower(storeReq.AddressNumber),\
        Store.CEP == storeReq.CEP\
        ).first()
    if addressQuery is not None:    
        return webResponse("Já existe um estabelecimento neste endereço", None), HttpCode.WARNING

    #Adiciona o estabelecimento novo ao banco de dados
    #Primeiro o Store para gerar o IdStore
    db.session.add(storeReq)
    db.session.commit()
    db.session.refresh(storeReq)

    employeeReq.IdStore = storeReq.IdStore

    db.session.add(employeeReq)
    db.session.commit()
    db.session.refresh(employeeReq)

    ###Ajustar esta parte no futuro
    employeeReq.EmailConfirmationToken = str(datetime.now().timestamp()) + str(employeeReq.IdEmployee)
    db.session.commit()
    emailStoreWelcomeConfirmation(employeeReq.Email, employeeReq.FirstName, "https://" + os.environ['URL_QUADRAS'] + "/emcf?str=1&tk="+employeeReq.EmailConfirmationToken)
    
    #Enviar e-mail para nós avisando
    emailStoreAwaitingApproval(storeReq, employeeReq, city)

    return webResponse("Você está quase lá!", \
    "Para concluir seu cadastro, é necessário que você valide seu e-mail.\nAcesse o link que enviamos e sua conta será criada.\n\nSe tiver qualquer dúvida, é só nos chamar, ok?"), HttpCode.ALERT

#Rota utilizada por nós para aprovar manualmente os estabelecimentos
@bp_store.route("/ApproveStore", methods=["POST"])
def ApproveStore():
    if not request.json:
        abort(HttpCode.ABORT)
        
    idStoreReq = request.json.get('IdStore')
    latitudeReq = request.json.get('Latitude')
    longitudeReq = request.json.get('Longitude')
    companyTypeReq = request.json.get('CompanyType')
    feeSandfriendsHighReq = request.json.get('FeeSandfriendsHigh')
    feeSandfriendsLowReq = request.json.get('FeeSandfriendsLow')
    feeThresholdReq = request.json.get('FeeThreshold')
    billingMethodReq = request.json.get('BillingMethod')
    storeUrl = request.json.get('StoreUrl')

    store = db.session.query(Store).filter(Store.IdStore == idStoreReq).first()

    if store is None:
        return "Loja não existe", HttpCode.EMAIL_NOT_FOUND

    if store.ApprovalDate is not None:
        return "Loja já aprovada anteriormente", HttpCode.STORE_ALREADY_APPROVED
        
    responseStore = createCustomer(store, companyTypeReq)
    
    if responseStore.status_code != 200:
        return "Erro Integração asaas" + responseStore.text, HttpCode.WARNING

    #Informações do Asaas - obtidas diretamente do Asaas
    store.AsaasId = responseStore.json().get('id')
    store.AsaasApiKey = responseStore.json().get('apiKey')
    store.AsaasWalletId = responseStore.json().get('walletId')

    #Informações extras
    store.Latitude = latitudeReq
    store.Longitude = longitudeReq
    store.CompanyType = companyTypeReq

    #Dados das taxas do Sandfriends - negociados individualmente
    store.FeeSandfriendsHigh = feeSandfriendsHighReq
    store.FeeSandfriendsLow = feeSandfriendsLowReq
    store.FeeThreshold = feeThresholdReq

    #Método que o Sandfriends irá cobrar do estabelecimento
    #PercentageFeesIncluded - Taxa do Sandfriends já inclui as taxas do Asaas
    #PercentageFeesNotIncluded - Taxa do Sandfriends não inclui taxas do Asaas
    #FixedPrice - Cobramos uma mensalidade fixa da quadra
    store.BillingMethod = billingMethodReq

    #Salva a data atual como ApprovalDate
    store.ApprovalDate = datetime.now()

    #busca o dono da qudra para enviar o email avisando q a quadra está ok
    employee = db.session.query(Employee).filter(Employee.StoreOwner == True)\
                                         .filter(Employee.IdStore == idStoreReq).first()

    emailStoreApproved(employee.Email, employee.FirstName)

    db.session.commit()

    return "Loja aprovada com sucesso", HttpCode.SUCCESS

@bp_store.route("/GetStores", methods=["GET"])
def GetStores():
    stores = Store.query.all()
    return jsonify([store.to_json() for store in stores])

@bp_store.route('/GetStore/<storeUrl>', methods = ['GET'])
def GetStore(storeUrl):
    store = Store.query.filter(Store.Url == storeUrl).first()

    if store is None or store.IsAvailable == False:
        return "Quadra não encontrada", HttpCode.WARNING
    return jsonify(store.to_json())

#rota utilizado pelo site sandfriends. Como o jogador pode entrar diretamente no url da store, tem que enviar aqui não só as infos da loj, mas os dados basicos
@bp_store.route('/GetStoreAndAuthenticate', methods = ['POST'])
def GetStoreAndAuthenticate():
    if not request.json:
        abort(400)

    storeUrlReq = request.json.get('StoreUrl')
    store = Store.query.filter(Store.Url == storeUrlReq).first()

    if store is None or store.IsAvailable == False:
        return "Quadra não encontrada", HttpCode.WARNING
    return  jsonify(store.to_json())

#rota utilizado pelo site sandfriends. Como o jogador pode entrar diretamente no url da store, tem que enviar aqui não só as infos da loj, mas os dados basicos
@bp_store.route('/GetStoreOperationHours/<storeId>', methods = ['GET'])
def GetStoreOperationHours(storeId):
    store = Store.query.filter(Store.IdStore == storeId).first()

    if store is None or store.IsAvailable == False:
        return "Quadra não encontrada", HttpCode.WARNING

    courtsIds = [court.IdStoreCourt for court in store.Courts]
    
    priceHours = db.session.query(StorePrice).filter(StorePrice.IdStoreCourt.in_(courtsIds)).all()

    operationHours = []
    for weekday in range(7):
        prices = [priceHour.IdAvailableHour for priceHour in priceHours if priceHour.Weekday == weekday]
        
        if prices:
            minHour = min(prices)
            maxHour = max(prices)
        operationHours.append({
            "Weekday": weekday,
            "StartingHour": minHour,
            "EndingHour": maxHour,
        })

    return  jsonify(operationHours),  HttpCode.SUCCESS

@bp_store.route("/UpdateStoreInfo", methods=["POST"])
def UpdateStoreInfo():
    if not request.json:
        abort(400)

    storeIdReq = request.json.get('IdStore')
    
    store = Store.query.get(storeIdReq)
    if store is None:
        return webResponse("Ops", "Tivemos um problema. Tente fazer login novamente."), HttpCode.WARNING

    cityReq = request.json.get('City')
    stateReq = request.json.get('State')

    nameReq = request.json.get('Name')
    addressReq = request.json.get('Address')
    addressNumberReq = request.json.get('AddressNumber')
    phoneNumber1Req = request.json.get('PhoneNumber1')
    descriptionReq = request.json.get('Description')
    cepReq = request.json.get('Cep')
    neighbourhoodReq = request.json.get('Neighbourhood')
    photosReq = request.json.get('Photos')

    #primeiro recebe a cidade e o estado pra ver pegar o stateId e o cityId
    city = db.session.query(City).filter(func.lower(City.City) == func.lower(cityReq)).first()
    state = db.session.query(State).filter(func.lower(State.UF) == func.lower(stateReq)).first()

    #Verificações de Cidade e Estado
    if city is None:
        return webResponse("Cidade não encontrada", None), HttpCode.WARNING

    if state is None:
        return webResponse("Estado não encontrado", None), HttpCode.WARNING

    if city.IdState != state.IdState:
        return webResponse("Esta cidade não pertence a esse estado", None), HttpCode.WARNING

    if store.IsAvailable:
        if(nameReq is None or nameReq == ""):
            return webResponse("O nome do seu estabelecimento está em branco", None), HttpCode.WARNING
        
        if(addressReq is None or addressReq == ""):
            return webResponse("A rua do seu estabelecimento está em branco", None), HttpCode.WARNING
        
        if(addressNumberReq is None or addressNumberReq == ""):
            return webResponse("O número do seu estabelecimento está em branco", None), HttpCode.WARNING
        
        if(phoneNumber1Req is None or phoneNumber1Req == ""):
            return webResponse("O telefone do seu estabelecimento está em branco", None), HttpCode.WARNING
        
        if(descriptionReq is None or descriptionReq == ""):
            return webResponse("A descrição do seu estabelecimento está em branco", None), HttpCode.WARNING
        
        if(cepReq is None or cepReq == ""):
            return webResponse("O CEP do seu estabelecimento está em branco", None), HttpCode.WARNING
        
        if(neighbourhoodReq is None or neighbourhoodReq == ""):
            return webResponse("O nome do bairro do seu estabelecimento está em branco", None), HttpCode.WARNING
        
        if (len(photosReq) < 3):
            return webResponse("Seu estabelecimento precisa ter pelo menos 3 fotos", None), HttpCode.WARNING
        
    store.Name = nameReq
    store.Address = addressReq
    store.AddressNumber = addressNumberReq
    store.IdCity = city.IdCity
    store.PhoneNumber1 = phoneNumber1Req
    store.PhoneNumber2 = request.json.get('PhoneNumber2')
    store.Description = descriptionReq
    store.Instagram = request.json.get('Instagram')
    store.CEP = cepReq
    store.Neighbourhood = neighbourhoodReq

    logoReq = request.json.get('Logo')
    if logoReq != "":
        photoName = str(store.IdStore) + str(datetime.now().strftime('%Y%m%d%H%M%S'))
        store.Logo = photoName
        imageBytes = base64.b64decode(logoReq + '==')
        imageFile = open(f'/var/www/html/img/str/logo/{store.Logo}.png', 'wb')
        imageFile.write(imageBytes)
        imageFile.close()

    
    receivedIdStorePhotos = []
    newPhotos = []

    for photo in photosReq:
        if photo["IdStorePhoto"] is None or photo["IdStorePhoto"] == "":
            newPhotos.append(str(photo["Photo"]))
        else:
            receivedIdStorePhotos.append(int(photo["IdStorePhoto"]))

    storePhotos = db.session.query(StorePhoto).filter(StorePhoto.IdStore == store.IdStore)\
                                .filter(StorePhoto.Deleted == False).all()
    for storePhoto in storePhotos:
        if storePhoto.IdStorePhoto not in receivedIdStorePhotos:
            storePhoto.Deleted = True

    for newPhoto in newPhotos:
        
        newStorePhoto = StorePhoto(
            Deleted = False,
            IdStore = store.IdStore,
        )
        db.session.add(newStorePhoto)
        db.session.commit()
        db.session.refresh(newStorePhoto)
        imageBytes = base64.b64decode(newPhoto + '==')
        imageFile = open(f'/var/www/html/img/str/{newStorePhoto.IdStorePhoto}.png', 'wb')
        imageFile.write(imageBytes)
        imageFile.close()

    db.session.commit()

    return {"Store": store.to_json()}, HttpCode.SUCCESS

@bp_store.route("/DeleteStore/<id>", methods=["DELETE"])
def DeleteStore(id):
    store = Store.query.get(id)
    db.session.delete(store)
    db.session.commit()
    return jsonify({'result': True})

def getAvailableStores():
    stores = db.session.query(Store)\
            .filter(Store.ApprovalDate != None)\
            .filter(Store.Latitude != None)\
            .filter(Store.Longitude != None)\
            .filter(Store.Description != None)\
            .filter(Store.Logo != None).all()
    
    storesList = []
    for store in stores:
        validPhotos = len([photo for photo in store.Photos if photo.Deleted==False])
        if((validPhotos >= 2) and (len(store.Courts) >=1)):
            storesList.append(store)
    return storesList