from flask import Blueprint, jsonify, abort, request
from flask_cors import cross_origin
from datetime import datetime, timedelta
from ..Models.store_model import Store
from ..extensions import db
from ..Models.http_codes import HttpCode
from ..Models.city_model import City
from ..Models.state_model import State
from ..Models.sport_model import Sport
from ..Models.available_hour_model import AvailableHour
from ..Models.store_court_model import StoreCourt
from ..emails import sendEmail
from ..Models.store_access_token_model import StoreAccessToken
from ..access_token import EncodeToken, DecodeToken

daysToExpireToken = 7

bp_store = Blueprint('bp_store', __name__)

@bp_store.route('/StoreLogin', methods=['POST'])
def StoreLogin():
    if not request.json:
        abort(400)

    emailReq = request.json.get('Email')
    passwordReq = request.json.get('Password')

    store = db.session.query(Store).filter(Store.Email == emailReq).first()
    if store is None:
        return "Email não cadastrado", HttpCode.EMAIL_NOT_FOUND
    if store.Password != passwordReq:
        return "Senha incorreta", HttpCode.INVALID_PASSWORD
    #senha correta

    if store.EmailConfirmationDate == None:
        return "E-mail não validado", HttpCode.WAITING_EMAIL_CONFIRMATION
    #email validado já

    if store.ApprovalDate == None:
        return "Estamos verificando as suas informações, entraremos em contato em breve", HttpCode.WAITING_APPROVAL
    #quadra já aprovada

    #Gera o AccessToken para os próximos logins
    currentDate = datetime.now()

    newStoreAccessToken = StoreAccessToken(
        IdStore = store.IdStore,
        AccessToken = EncodeToken(store.IdStore),
        CreationDate = currentDate,
        LastAccessDate = currentDate
    )

    db.session.add(newStoreAccessToken)
    db.session.commit()

    #retorna as informações da quadra (esportes, horários, etc)
    return initStoreLoginData(store), HttpCode.SUCCESS

@bp_store.route('/ValidateStoreAccessToken', methods=['POST'])
def ValidateStoreAccessToken():
    if not request.json:
        abort(400)
    
    receivedToken = request.json.get('AccessToken')

    storeAccessToken = db.session.query(StoreAccessToken).filter(StoreAccessToken.AccessToken == receivedToken).first()

    #Caso não encontrar Token
    if storeAccessToken is None:
        return "Token não encontrado", HttpCode.INVALID_ACCESS_TOKEN

    #Verificar se o Token é válido
    if (datetime.now() - storeAccessToken.LastAccessDate).days > daysToExpireToken:
        return "Token expirado", HttpCode.INVALID_ACCESS_TOKEN

    #Token está válido - atualizar o LastAccessDate
    storeAccessToken.LastAccessDate = datetime.now()
    db.session.commit()

    #Token válido - retorna as informações da quadra (esportes, horários, etc)
    return initStoreLoginData(storeAccessToken.Store), HttpCode.SUCCESS

@bp_store.route('/AddStore', methods=['POST'])
def AddStore():
    if not request.json:
        abort(400)
    receivedCity = request.json.get('City'),
    receivedState = request.json.get('State'),

    city = db.session.query(City).filter(City.City == receivedCity).first()
    state = db.session.query(State).filter(State.UF == receivedState).first()
    sameCnpj = db.session.query(Store).filter(Store.CNPJ == request.json.get('CNPJ')).first()
    sameEmail = db.session.query(Store).filter(Store.Email == request.json.get('Email')).first()

    if city is None:
        return "Cidade não encontrada", HttpCode.CITY_NOT_FOUND

    if state is None:
        return "Estado não encontrado", HttpCode.STATE_NOT_FOUND

    if city.IdState != state.IdState:
        return "Esta cidade não pertence a esse estado", HttpCode.CITY_STATE_NOT_MATCH

    if sameCnpj is not None:
        return "CNPJ já cadastrado", HttpCode.CNPJ_ALREADY_USED

    if sameEmail is not None:
        return "Email já cadastrado", HttpCode.EMAIL_ALREADY_USED

    store = Store(
        Name = request.json.get('Name'),
        Address = request.json.get('Address'),
        IdCity = city.IdCity,
        Email = request.json.get('Email'),
        PhoneNumber1 = request.json.get('Telephone'),
        PhoneNumber2 = request.json.get('TelephoneOwner'),
        Description = request.json.get('Description'),
        Instagram = request.json.get('Instagram'),
        CNPJ = request.json.get('CNPJ'),
        CEP = request.json.get('CEP'),
        Neighbourhood = request.json.get('Neighbourhood'),
        OwnerName = request.json.get('OwnerName'),
        CPF = request.json.get('CPF'),
        RegistrationDate = datetime.now()
    )
    db.session.add(store)
    db.session.commit()
    db.session.refresh(store)

    store.EmailConfirmationToken = str(datetime.now().timestamp()) + str(store.IdStore)
    sendEmail("https://www.sandfriends.com.br/redirect/?ct=emcf&bd="+store.EmailConfirmationToken)
    return "ok", HttpCode.SUCCESS


@bp_store.route('/ForgotPasswordStore', methods=['POST'])
def ForgotPasswordStore():
    if not request.json:
        abort(400)
    
    emailReq = request.json.get('Email')

    store = db.session.query(Store).filter(Store.Email == emailReq).first()

    #verifica se o email já está cadastrado
    if store is None:
        return "Email não cadastrado", HttpCode.EMAIL_NOT_FOUND
    #verifica se a loja já foi aprovada
    if store.ApprovalDate is None:
        return "Aguarde a verificação pela equipe do Sand Friends", HttpCode.WAITING_APPROVAL

    #envia o email automático para redefinir a senha
    ### ver porque ele faz esse cálculo do datetime + email confirmation token, não poderia ser algo aleatorio?
    store.ResetPasswordToken = str(datetime.now().timestamp()) + store.EmailConfirmationToken
    db.session.commit()
    sendEmail("Troca de senha <br/> https://www.sandfriends.com.br/redirect/?ct=cgpw&bd="+store.ResetPasswordToken)
    return 'Código enviado para redefinir a senha', HttpCode.SUCCESS

@bp_store.route('/ChangePasswordStore', methods=['POST'])
def ChangePasswordStore():
    if not request.json:
        abort(400)

    resetPasswordTokenReq = request.json.get('resetPasswordToken')
    newPassword = request.json.get('newPassword')
    newPassword2 = request.json.get('newPassword2')

    store = db.session.query(Store).filter(Store.ResetPasswordToken == resetPasswordTokenReq).first()

    #verifica se o token está certo
    if store is None:
        return "Token inválido", HttpCode.INVALID_RESET_PASSWORD_VALUE

    #verifica se as duas senhas são as mesmas
    if newPassword != newPassword2:
        return "Senhas não coincidem", HttpCode.INVALID_PASSWORD

    #adiciona a senha no banco de dados
    store.Password = newPassword

    #anula o resetPasswordToken
    store.ResetPasswordToken = None

    #anual os tokens de acesso
    #deixa a data de LastAccess deles como 10 ano atrás
    tokens = db.session.query(StoreAccessToken).filter(StoreAccessToken.IdStore == store.IdStore).all()
    for token in tokens:
        token.LastAccessDate = token.LastAccessDate - timedelta(days=10*365)
        
    db.session.commit()
    return 'Senha alterada com sucesso', HttpCode.SUCCESS

#Rota utilizada pelo gestor quando ele clica no link pra confirmação do email, após criar a conta
@bp_store.route("/ConfirmEmailStore", methods=["POST"])
def ConfirmEmailStore():
    if not request.json:
        abort(HttpCode.ABORT)

    emailConfirmationTokenReq = request.json.get('emailConfirmationToken')
    store = db.session.query(Store).filter(Store.EmailConfirmationToken == emailConfirmationTokenReq).first()
    
    if store is None:
        return "Token de confirmação inválido", HttpCode.INVALID_EMAIL_CONFIRMATION_TOKEN

    if store.EmailConfirmationDate is not None:
        return "Já confirmado anteriormente", HttpCode.EMAIL_ALREADY_CONFIRMED

    #Tudo ok com o token se chegou até aqui
    #Enviar e-mail avisando que estaremos verificando os dados da quadra e entraremos em contato em breve
    sendEmail("O seu email já está confirmado! <br><br>Estamos conferindo os seus dados e estaremos entrando em contato em breve quando estiver tudo ok.<br><br>")

    #Salva a data de confirmação da conta do gestor
    store.EmailConfirmationDate = datetime.now()
    db.session.commit()
    return "Email confirmado com sucesso", HttpCode.SUCCESS


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


def initStoreLoginData(store):

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

    return jsonify({'Sports' : sportsList, 'AvailableHours' : hoursList, 'Store' : store.to_json(), 'Courts' : courtsList})
