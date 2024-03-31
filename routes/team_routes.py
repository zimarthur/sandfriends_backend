from flask import Blueprint, jsonify, abort, request
from datetime import datetime
import random
from sqlalchemy import null, true, ForeignKey, func
from ..responses import webResponse
from ..Models.user_model import User
from ..Models.store_model import Store
from ..Models.available_hour_model import AvailableHour
from ..Models.store_court_model import StoreCourt
from ..Models.teacher_plan_model import TeacherPlan
from ..Models.sport_model import Sport
from ..Models.store_school_model import StoreSchool
from ..Models.team_model import Team
from ..Models.team_member_model import TeamMember
from ..Models.store_school_teacher_model import StoreSchoolTeacher
from ..extensions import db
from ..Models.http_codes import HttpCode
from ..access_token import EncodeToken, DecodeToken
from ..Models.employee_model import getEmployeeByToken
import bcrypt
import json
import os
import string
import random
import base64

bp_team = Blueprint('bp_team', __name__)

#Rota utilizada para fazer login de qualquer employee no site
@bp_team.route('/AddTeam', methods=['POST'])
def AddTeam():
    if not request.json:
        abort(HttpCode.ABORT)

    tokenReq = request.json.get('AccessToken')

    user = User.query.filter_by(AccessToken = tokenReq)\
                    .filter_by(IsTeacher = True).first()

    #Verifica se o token é 0 ou null
    if tokenReq == 0 or tokenReq is None:
        return "Token inválido, faça login novamente", HttpCode.EXPIRED_TOKEN

    if user is None:
        return 'Token inválido.', HttpCode.EXPIRED_TOKEN

    teamNameReq = request.json.get('Name')
    teamDescriptionReq = request.json.get('Description')
    idSportReq = request.json.get('IdSport')
    idRankReq = request.json.get('IdRank')
    idGenderReq = request.json.get('IdGender')
    
    newTeam = Team(
        IdUser = user.IdUser,
        Name= teamNameReq.title(),
        Description = teamDescriptionReq,
        IdSport = idSportReq,
        IdRankCategory = idRankReq,
        IdGenderCategory = idGenderReq,
        CreationDate = datetime.now()
    )

    db.session.add(newTeam)
    db.session.commit()
    db.session.refresh(newTeam)

    return jsonify({"NewTeam": newTeam.to_json()}), HttpCode.SUCCESS

@bp_team.route('/SchoolInvitationResponse', methods=['POST'])
def SchoolInvitationResponse():
    if not request.json:
        abort(HttpCode.ABORT)

    tokenReq = request.json.get('AccessToken')

    user = User.query.filter_by(AccessToken = tokenReq)\
                    .filter_by(IsTeacher = True).first()

    #Verifica se o token é 0 ou null
    if tokenReq == 0 or tokenReq is None:
        return "Token inválido, faça login novamente", HttpCode.EXPIRED_TOKEN

    if user is None:
        return 'Token inválido.', HttpCode.EXPIRED_TOKEN

    idTeacherReq = request.json.get('IdTeacher')
    acceptedReq = request.json.get('Accepted')

    storeTeacher = db.session.query(StoreSchoolTeacher).get(idTeacherReq)

    if storeTeacher is None:
        return 'Escola não encontrada, atualize a págine ou entre em contato com o suporte', HttpCode.WARNING

    storeTeacher.WaitingApproval = False
    storeTeacher.Refused = acceptedReq == False
    storeTeacher.ResponseDate = datetime.now()

    db.session.commit()

    return jsonify({"SchoolTeacher": storeTeacher.to_json_teacher()}), HttpCode.SUCCESS

