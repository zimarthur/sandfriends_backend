from flask import Blueprint, jsonify, abort, request
from flask_cors import cross_origin
from datetime import datetime, timedelta, date
from ..Models.store_model import Store
from ..extensions import db
from ..responses import webResponse
from ..Models.http_codes import HttpCode
from ..Models.city_model import City
from ..Models.state_model import State
from ..Models.sport_model import Sport
from ..Models.match_model import Match
from ..Models.employee_model import Employee
from ..Models.available_hour_model import AvailableHour
from ..Models.store_court_model import StoreCourt
from ..emails import sendEmail
from ..Models.employee_access_token_model import EmployeeAccessToken
from ..access_token import EncodeToken, DecodeToken
from sqlalchemy import func

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

    #Employee que será criado automaticamente - o dono da quadra
    employeeReq = Employee(
        Email = (request.json.get('Email')).lower(),
        FirstName = (request.json.get('FirstName')).title(),
        LastName = (request.json.get('LastName')).title(),
        Password = request.json.get('Password'),
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
    sendEmail("https://www.sandfriends.com.br/emcf?str=1&tk="+employeeReq.EmailConfirmationToken)
    return webResponse("Você está quase lá!", \
    "Para concluir seu cadastro, é necessário que você valide seu e-mail.\nAcesse o link que enviamos e sua conta será criada.\n\nSe tiver qualquer dúvida, é só nos chamar, ok?"), HttpCode.ALERT



#Rota utilizada por nós para aprovar manualmente os estabelecimentos
@bp_store.route("/ApproveStore", methods=["POST"])
def ApproveStore():
    if not request.json:
        abort(HttpCode.ABORT)
        
    idStoreReq = request.json.get('IdStore')
    store = db.session.query(Store).filter(Store.IdStore == idStoreReq).first()

    if store is None:
        return "Loja não existe", HttpCode.EMAIL_NOT_FOUND

    if store.ApprovalDate is not None:
        return "Loja já aprovada anteriormente", HttpCode.STORE_ALREADY_APPROVED
        
    #Salva a data atual como ApprovalDate
    store.ApprovalDate = datetime.now()

    #busca o dono da qudra para enviar o email avisando q a quadra está ok
    employee = db.session.query(Employee).filter(Employee.StoreOwner == True)\
                                         .filter(Employee.IdStore == idStoreReq).first()

    #TODO: adicionar destinatário
    sendEmail("Sua quadra está ok")

    db.session.commit()

    return "Loja aprovada com sucesso", HttpCode.SUCCESS

@bp_store.route("/GetStores", methods=["GET"])
def GetStores():
    stores = Store.query.all()
    return jsonify([store.to_json() for store in stores])

@bp_store.route('/GetStore/<id>', methods = ['GET'])
def GetStore(id):
    store = Store.query.get(id)
    return jsonify(store.to_json())

@bp_store.route("/UpdateStore/<id>", methods=["PUT"])
def UpdateStore(id):
    if not request.json:
        abort(400)
    store = Store.query.get(id)
    if store is None:
        abort(404)
    store.Name = request.json.get('Name')
    store.Address = request.json.get('Address')
    store.IdCity = request.json.get('City')
    store.Email = request.json.get('Email')
    store.PhoneNumber1 = request.json.get('PhoneNumber1')
    store.PhoneNumber2 = request.json.get('PhoneNumber2')
    store.Description = request.json.get('Description')
    store.Instagram = request.json.get('Instagram')
    db.session.commit()
    return jsonify(store.to_json())

@bp_store.route("/DeleteStore/<id>", methods=["DELETE"])
def DeleteStore(id):
    store = Store.query.get(id)
    db.session.delete(store)
    db.session.commit()
    return jsonify({'result': True})


def initStoreLoginData(store, accessToken):
    startTime = datetime.now()
    #Lista com todos esportes
    sports = db.session.query(Sport).all()
    sportsList = []

    for sport in sports:
        sportsList.append(sport.to_json())

    #Lista com todas horas do dia
    hours = db.session.query(AvailableHour).all()
    hoursList = []

    for hour in hours:
        hoursList.append(hour.to_json())

    #Lista com as quadras do estabelecimento(json da quadra, esportes e preço)
    courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == store.IdStore).all()
    courtsList = []

    for court in courts:
        courtsList.append(court.to_json_full())

    matches = db.session.query(Match).filter(Match.IdStoreCourt.in_([court.IdStoreCourt for court in courts]))\
    .filter(Match.Date >= date(2023, 4, 1)).filter(Match.Date <= date(2023, 5, 30)).all()
    matchList =[]
    for match in matches:
        matchList.append(match.to_json())
    endTime =  datetime.now()
    return jsonify({'AccessToken':accessToken, 'Sports' : sportsList, 'AvailableHours' : hoursList, 'Store' : store.to_json(), 'Courts' : courtsList, 'Matches':matchList})
    