from flask import Blueprint, jsonify, abort, request
from datetime import datetime
import random
from sqlalchemy import null, true, ForeignKey, func
from ..responses import webResponse
from ..Models.user_model import User
from ..Models.store_model import Store
from ..Models.available_hour_model import AvailableHour
from ..Models.store_court_model import StoreCourt
from ..Models.sport_model import Sport
from ..Models.store_school_model import StoreSchool
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


bp_store_schools = Blueprint('bp_store_schools', __name__)

# Rota para criar escola
@bp_store_schools.route("/AddSchool", methods=["POST"])
def AddSchool():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessTokenReq = request.json.get('AccessToken')

    employee = getEmployeeByToken(accessTokenReq)

    #Caso não encontrar Token
    if employee is None:
        return webResponse("Sua sessão expirou!", None), HttpCode.EXPIRED_TOKEN

    #Verificar se o Token é válido
    if employee.isAccessTokenExpired():
        return webResponse("Sua sessão expirou!", None), HttpCode.EXPIRED_TOKEN

    nameReq = request.json.get('Name')
    idSportReq = request.json.get('IdSport')

    concurrentStoreSchool =  db.session.query(StoreSchool).filter(func.lower(StoreSchool.Name) == func.lower(nameReq))\
                                                    .filter(StoreSchool.IdSport == idSportReq).first()

    if concurrentStoreSchool is not None:
        return webResponse("Essa escola já existe", "Já existe uma escola com esse nome e esporte no seu estabelecimento"), HttpCode.WARNING

    
        
    newSchool = StoreSchool(
        Name = nameReq.title(),
        IdSport = idSportReq,
        CreationDate = datetime.now(),
        IdStore = employee.IdStore,
    )
    db.session.add(newSchool)
    db.session.commit()
    db.session.refresh(newSchool)

    logoReq = request.json.get('Logo')
    if logoReq is not None:
        photoName = str(newSchool.IdStoreSchool) + str(datetime.now().strftime('%Y%m%d%H%M%S'))
        newSchool.Logo = photoName
        imageBytes = base64.b64decode(logoReq + '==')
        imageFile = open(f'/var/www/html/img/sch/{photoName}.png', 'wb')
        imageFile.write(imageBytes)
        imageFile.close()

    db.session.commit()
    db.session.refresh(newSchool)

    return jsonify({ "NewSchool": newSchool.to_json()}), HttpCode.SUCCESS

# Rota para editar escola
@bp_store_schools.route("/EditSchool", methods=["POST"])
def EditSchool():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessTokenReq = request.json.get('AccessToken')

    employee = getEmployeeByToken(accessTokenReq)

    #Caso não encontrar Token
    if employee is None:
        return webResponse("Sua sessão expirou!", None), HttpCode.EXPIRED_TOKEN

    #Verificar se o Token é válido
    if employee.isAccessTokenExpired():
        return webResponse("Sua sessão expirou!", None), HttpCode.EXPIRED_TOKEN

    storeSchoolReq = request.json.get('IdStoreSchool')

    storeSchool = db.session.query(StoreSchool).get(storeSchoolReq)

    if storeSchool is None:
        return webResponse("Escola não econtrada", "Entre em contato com o suporte"), HttpCode.WARNING

    storeSchool.Name = request.json.get('Name').title()

    logoReq = request.json.get('Logo')

    if logoReq is not None:
        photoName = str(storeSchool.IdStoreSchool) + str(datetime.now().strftime('%Y%m%d%H%M%S'))
        storeSchool.Logo = photoName
        imageBytes = base64.b64decode(logoReq + '==')
        imageFile = open(f'/var/www/html/img/sch/{photoName}.png', 'wb')
        imageFile.write(imageBytes)
        imageFile.close()

    db.session.commit()
    db.session.refresh(storeSchool)

    return jsonify({ "EditSchool": storeSchool.to_json()}), HttpCode.SUCCESS


