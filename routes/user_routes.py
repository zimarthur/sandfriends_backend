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


@bp_user.route("/UpdateUser", methods=["POST"])
def UpdateUser():
    if not request.json:
        abort(HttpCode.ABORT)
    
    user = User.query.filter_by(AccessToken = request.json.get('AccessToken')).first()
    
    if user is None:
        return 'Token invalido', HttpCode.WARNING
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

        photoReq = request.json.get('Photo')
        if user.Photo is None or user.Photo not in photoReq:
            if photoReq is None or photoReq == "":
                user.Photo = None
            else: 
                photoName = str(user.IdUser) + str(datetime.now().strftime('%Y%m%d%H%M%S'))
                user.Photo = photoName
                imageBytes = base64.b64decode(photoReq + '==')
                imageFile = open(f'/var/www/html/img/usr/{user.Photo}.png', 'wb')
                imageFile.write(imageBytes)
                imageFile.close()

        db.session.commit()
        return user.to_json(), HttpCode.SUCCESS