from flask import Blueprint, jsonify, abort, request
from flask_cors import cross_origin
from datetime import datetime
from ..Models.store_model import Store
from ..extensions import db
from ..Models.http_codes import HttpCode
from ..Models.city_model import City
from ..Models.state_model import State
from ..emails import sendEmail

bp_store = Blueprint('bp_store', __name__)

@bp_store.route('/StoreLogin', methods=['POST'])
@cross_origin()
def StoreLogin():
    print("1111111")
    if not request.json:
        abort(400)
    print("2222222")
    email = db.session.query(Store).filter(Store.Email == request.json.get('Email')).first()
    if email is None:
        return "Email não cadastrado", HttpCode.EMAIL_NOT_FOUND
    print("3333333")
    if email.Password != request.json.get('Password'):
        return "Senha incorreta", HttpCode.INVALID_PASSWORD
    print("444444")
    return "ok", HttpCode.SUCCESS

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
        return "Cnpj já cadastrado", HttpCode.CNPJ_ALREADY_USED

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
        Validated = False,
        RegistrationDate = datetime.now()
    )
    db.session.add(store)
    db.session.commit()
    db.session.refresh(store)

    store.EmailConfirmationToken = str(datetime.now().timestamp()) + str(store.IdStore)
    sendEmail("https://www.sandfriends.com.br/redirect/?ct=emcf&bd="+store.EmailConfirmationToken)
    return "ok", HttpCode.SUCCESS


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