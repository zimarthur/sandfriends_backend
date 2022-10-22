from flask import Blueprint, jsonify, abort, request
from ..Models.store_model import Store
from ..extensions import db

bp_store = Blueprint('bp_store', __name__)

@bp_store.route('/AddStore', methods=['POST'])
def AddStore():
    if not request.json:
        abort(400)
    store = Store(
        Name = request.json.get('Name'),
        Address = request.json.get('Address'),
        IdCity = request.json.get('City'),
        Email = request.json.get('Email'),
        PhoneNumber1 = request.json.get('PhoneNumber1'),
        PhoneNumber2 = request.json.get('PhoneNumber2'),
        Logo = request.json.get('Logo'),
        Description = request.json.get('Description'),
        Instagram = request.json.get('Instagram'),
    )
    db.session.add(store)
    db.session.commit()
    return jsonify(store.to_json()), 201

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