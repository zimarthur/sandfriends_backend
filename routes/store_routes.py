from flask import Blueprint, jsonify, abort, request
from datetime import datetime
from ..Models.store_model import Store
from ..extensions import db
from ..Models.http_codes import HttpCode
from ..Models.city_model import City
from ..Models.state_model import State

bp_store = Blueprint('bp_store', __name__)

@bp_store.route('/AddStore', methods=['POST'])
def AddStore():
    if not request.json:
        abort(400)
    receivedCity = request.json.get('City'),
    receivedState = request.json.get('State'),

    city = db.session.query(City).filter(City.City == receivedCity).first()
    state = db.session.query(State).filter(State.UF == receivedState).first()

    if city is None:
        return "No city Found", HttpCode.CITY_NOT_FOUND

    if state is None:
        return "No state Found", HttpCode.STATE_NOT_FOUND

    if city.IdState != state.IdState:
        return "City not in state", HttpCode.CITY_STATE_NOT_MATCH

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