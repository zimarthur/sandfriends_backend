from flask import Blueprint, jsonify, abort, request
from ..Models.store_photo_model import StorePhoto
from ..extensions import db

bp_store_price = Blueprint('bp_store_price', __name__)

@bp_store_price.route("/AddStorePhoto", methods=["POST"])
def AddStorePhoto():
    if not request.json:
        abort(400)
    storePhoto = StorePhoto(
        IdStore = request.json.get('IdStore'),
    #ADICIONAR ETAPA DE SALVAR IMAGEM
    )
    db.session.add(storePhoto)
    db.session.commit()
    return jsonify(storePhoto.to_json()), 201
    
@bp_store_price.route("/GetStorePhotos/<storeId>", methods=["GET"])
def GetStorePhotos(storeId):
    storephotos = StorePhoto.query.filter_by(IdStore = storeId)
    return jsonify([storephoto.to_json() for storephoto in storephotos])

@bp_store_price.route("/DeleteStorePhoto/<idStorePhoto>", methods=["DELETE"])
def DeleteStorePhoto(idStorePhoto):
    storePhoto = StorePhoto.query.get(idStorePhoto)
    db.session.delete(storePhoto)
    db.session.commit()
    return jsonify({'result': True})