from flask import Blueprint, jsonify, abort, request
import base64

from ..Models.user_model import User
from ..Models.user_login_model import UserLogin
from ..Models.user_rank_model import UserRank
from ..Models.sport_model import Sport
from ..Models.rank_category_model import RankCategory
from ..extensions import db
from ..routes import user_login_routes
from ..Models.http_codes import HttpCode
from datetime import datetime


bp_user = Blueprint('bp_user', __name__)

@bp_user.route('/AddUser', methods=['POST'])
def AddUser():
    if not request.json:
        abort(400)

    payloadUserId = user_login_routes.DecodeToken(request.json.get('AccessToken'))
    user = User(
        IdUser = payloadUserId,
        FirstName = request.json.get('FirstName'),
        LastName = request.json.get('LastName'),
        PhoneNumber = request.json.get('PhoneNumber'),
        IdGenderCategory = None,
        Birthday = None,
        Height = None,
        IdSidePreferenceCategory = None,
        Photo = None,
        IdCity = request.json.get('IdCity'),
        IdSport = request.json.get('IdSport'),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_json()), 201

@bp_user.route("/GetUsers", methods=["GET"])
def GetUsers():
    users = User.query.all()
    return jsonify([user.to_json() for user in users])

@bp_user.route('/GetUser/<accessToken>', methods = ['GET'])
def GetUser(accessToken):
    userLogin = UserLogin.query.filter_by(AccessToken = accessToken).first()
    if userLogin is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN
    else:
        user = User.query.get(userLogin.IdUser)
        return jsonify(user.to_json()), HttpCode.SUCCESS


@bp_user.route("/UpdateUser", methods=["PUT"])
def UpdateUser():
    if not request.json:
        abort(HttpCode.ABORT)
    
    userLogin = UserLogin.query.filter_by(AccessToken = request.json.get('AccessToken')).first()

    if userLogin is None:
        return 'NOK', HttpCode.INVALID_ACCESS_TOKEN
    else:
        availableRanks = db.session.query(RankCategory).all()
        availableSports = db.session.query(Sport).all()

        newRanks = request.json.get('Rank')

        for sport in availableSports:
            sportRanks = [availableRank for availableRank in availableRanks if availableRank.IdSport == sport.IdSport]
            for newRank in newRanks:
                if newRank['idSport'] == sport.IdSport:
                    oldUserRanks = db.session.query(UserRank)\
                                .filter(UserRank.IdUser == userLogin.IdUser)\
                                .filter(UserRank.IdRankCategory.in_([sportRank.IdRankCategory for sportRank in sportRanks])).first()
                    if oldUserRanks is None:
                        rank = UserRank(
                            IdUser = userLogin.IdUser,
                            IdRankCategory = newRank['idRankCategory'],
                        )
                        db.session.add(rank)
                    else:
                        oldUserRanks.IdRankCategory = newRank['idRankCategory']
                    db.session.commit()

        user = User.query.get(userLogin.IdUser)
        user.FirstName = request.json.get('FirstName')
        user.LastName = request.json.get('LastName')
        user.PhoneNumber = request.json.get('PhoneNumber')
        user.IdSport = request.json.get('IdSport')
        if request.json.get('IdGender') == "":
            user.IdGenderCategory = None
        else:
            user.IdGenderCategory = request.json.get('IdGender')
        if request.json.get('IdCity') == "":
            user.IdCity = None
        else:
            user.IdCity = request.json.get('IdCity')
        if request.json.get('Birthday') == "":
            user.Birthday = None
        else:
            user.Birthday = request.json.get('Birthday')
        if request.json.get('Height') == "":
            user.Height = None
        else:
            user.Height = request.json.get('Height')
        if request.json.get('SidePreference') == "":
            user.IdSidePreferenceCategory = None
        else:
            user.IdSidePreferenceCategory = request.json.get('SidePreference')

        if request.json.get('Photo') == "":
            user.Photo = None
        else:
            user.Photo = str(userLogin.RegistrationDate.timestamp()).replace(".","") + str(userLogin.IdUser)
            decoded_data=base64.b64decode(request.json.get('Photo')+ '==')
            img_file = open(f'/var/www/html/img/usr/{user.Photo}.png', 'wb')
            img_file.write(decoded_data)
            img_file.close()

        db.session.commit()
        return jsonify(user.to_json()), HttpCode.SUCCESS

@bp_user.route("/DeleteUser/<id>", methods=["DELETE"])
def DeleteUser(id):
    user = User.query.get(id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'result': True})