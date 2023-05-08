from flask import Blueprint, jsonify, abort, request
import base64

from ..Models.user_model import User
from ..Models.user_rank_model import UserRank
from ..Models.sport_model import Sport
from ..Models.rank_category_model import RankCategory
from ..extensions import db
from ..routes import user_login_routes
from ..Models.http_codes import HttpCode
from datetime import datetime
import os


bp_user = Blueprint('bp_user', __name__)

@bp_user.route('/AddUserInformation', methods=['POST'])
def AddUserInformation():
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

    rankCategories = db.session.query(RankCategory).all()

    for rankCategory in rankCategories:
        if rankCategory.RankSportLevel == 0:
            userRank = UserRank(
                IdUser = user.IdUser,
                IdRankCategory = rankCategory.IdRankCategory,
            )
            db.session.add(userRank)
    db.session.commit()
    return jsonify(user.to_json()), 201

@bp_user.route("/UpdateUser", methods=["POST"])
def UpdateUser():
    if not request.json:
        abort(HttpCode.ABORT)
    
    user = User.query.filter_by(AccessToken = request.json.get('AccessToken')).first()

    if user is None:
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
                                .filter(UserRank.IdUser == user.IdUser)\
                                .filter(UserRank.IdRankCategory.in_([sportRank.IdRankCategory for sportRank in sportRanks])).first()
                    if oldUserRanks is None:
                        rank = UserRank(
                            IdUser = user.IdUser,
                            IdRankCategory = newRank['idRankCategory'],
                        )
                        db.session.add(rank)
                    else:
                        oldUserRanks.IdRankCategory = newRank['idRankCategory']

        user = User.query.get(user.IdUser)
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

        # if request.json.get('Photo') == "":
        #     user.Photo = None
        # else:
        #     user.Photo = str(user.RegistrationDate.timestamp()).replace(".","") + str(user.IdUser)
        #     print(user.Photo)
        #     decoded_data=base64.b64decode(request.json.get('Photo')+ '==')
        #     img_file = open(f'/var/www/html/img/usr/{user.Photo}.png', 'wb')
        #     img_file.write(decoded_data)
        #     img_file.close()

        db.session.commit()
        return "Suas informações foram alteradas!", HttpCode.ALERT