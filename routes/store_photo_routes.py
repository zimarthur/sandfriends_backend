from flask import Blueprint, jsonify, abort, request
from ..Models.store_price_model import StorePrice
from ..extensions import db

bp_store_photo = Blueprint('bp_store_photo', __name__)

@bp_store_photo.route("/AddStorePriceUnique/<storeId>", methods=["POST"])
def AddStorePriceUnique(storeId):
    if not request.json:
        abort(400)
    
    for day in range(1,8):
        for hour in range(0,24):
            idExists = db.session.query(StorePrice.IdStorePrice).filter_by(IdStore = storeId, Day = day, Hour = hour).first()
            if idExists == None:
                storePrice = StorePrice(
                    IdStore = storeId,
                    Day = day,
                    Hour = hour,
                    Price = request.json.get('Price'),
                )
                db.session.add(storePrice)
            else:
                storePrice = StorePrice.query.get(idExists)
                storePrice.Price = request.json.get('Price')
    db.session.commit()
    return jsonify(storePrice.to_json()), 201


@bp_store_photo.route("/AddStorePriceByDay/<storeId>", methods=["POST"])
def AddStorePriceByDay(storeId):
    if not request.json:
        abort(400)

    modifications = 0
    receivedJson = request.get_json()
    for obj in receivedJson:
        day = obj.get('Day')
        hour = obj.get('Hour')
        price = obj.get('Price')
        
        idExists = db.session.query(StorePrice.IdStorePrice).filter_by(IdStore = storeId, Day = day, Hour = hour).first()

        if idExists == None:
                storePrice = StorePrice(
                    IdStore = storeId,
                    Day = day,
                    Hour = hour,
                    Price = price,
                )
                db.session.add(storePrice)
        else:
            storePrice = StorePrice.query.get(idExists)
            storePrice.Price = price
        modifications+=1
    db.session.commit()
    return(str(modifications))

@bp_store_photo.route("/AddStorePriceByWeek/<storeId>", methods=["POST"])
def AddStorePriceByWeek(storeId):
    if not request.json:
        abort(400)

    modifications = 0
    receivedJson = request.get_json()
    for obj in receivedJson:
        hour = obj.get('Hour')
        price = obj.get('Price')
        for day in range(1,8):
            idExists = db.session.query(StorePrice.IdStorePrice).filter_by(IdStore = storeId, Day = day, Hour = hour).first()

            if idExists == None:
                    storePrice = StorePrice(
                        IdStore = storeId,
                        Day = day,
                        Hour = hour,
                        Price = price,
                    )
                    db.session.add(storePrice)
            else:
                storePrice = StorePrice.query.get(idExists)
                storePrice.Price = price
            modifications+=1
    db.session.commit()
    return(str(modifications))