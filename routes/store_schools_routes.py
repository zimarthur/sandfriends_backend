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


# Rota para adicionar professor em escola
@bp_store_schools.route("/AddSchoolTeacher", methods=["POST"])
def AddSchoolTeacher():
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

    idStoreSchoolReq = request.json.get('IdStoreSchool')
    teacherEmailReq = request.json.get('TeacherEmail')

    storeSchool = db.session.query(StoreSchool).get(idStoreSchoolReq)

    if storeSchool is None:
        return webResponse("Escola não encontrada", "Tente atualizar a página. Se não conseguir, fale com o suporte"), HttpCode.WARNING

    teacher = db.session.query(User).filter(User.Email == teacherEmailReq)\
                                    .filter(User.IsTeacher == True)\
                                    .filter(User.DateDisabled == None).first()
    if teacher is None:
        return webResponse("Professor não encontrado", "Confirme que esse é o email utilizado pelo professor no cadastro do app de aulas"), HttpCode.WARNING

    newSchoolTeacher = StoreSchoolTeacher(
        IdStoreSchool = idStoreSchoolReq,
        IdUser = teacher.IdUser,
        WaitingApproval = True,
        Refused = False,
        RequestDate = datetime.now()
    )
    db.session.add(newSchoolTeacher)
    db.session.commit()
    db.session.refresh(storeSchool)

    return jsonify({ "EditSchool": storeSchool.to_json()}), HttpCode.SUCCESS

@bp_store_schools.route("/AddTeacherClassPlan", methods=["POST"])
def AddTeacherClassPlan():
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

    timesPerWeekReq = request.json.get('TimesPerWeek')
    classSizeReq = request.json.get('ClassSize')
    priceReq = request.json.get('Price')

    existingPlan = db.session.query(TeacherPlan)\
                        .filter(TeacherPlan.IdUser == user.IdUser)\
                        .filter(TeacherPlan.TimesPerWeek == timesPerWeekReq)\
                        .filter(TeacherPlan.ClassSize == classSizeReq).first()
    
    if existingPlan is not None:
        return 'Você já tem um plano nesse formato e frequência', HttpCode.WARNING

    newPlan = TeacherPlan(
        ClassSize =classSizeReq,
        TimesPerWeek =timesPerWeekReq,
        Price = priceReq,
        IdUser = user.IdUser,
    )
    db.session.add(newPlan)
    db.session.commit()
    db.session.refresh(newPlan)

    return jsonify({ "NewPlan": newPlan.to_json()}), HttpCode.SUCCESS


@bp_store_schools.route("/DeleteTeacherClassPlan", methods=["POST"])
def DeleteTeacherClassPlan():
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

    idClassPlanReq = request.json.get('IdClassPlan')


    existingPlan = db.session.query(TeacherPlan).get(idClassPlanReq)
    
    if existingPlan is None:
        return 'Plano não contrado. Por favor, atualize a página', HttpCode.WARNING

    db.session.delete(existingPlan)
    db.session.commit()
    
    return "Deletado", HttpCode.SUCCESS

@bp_store_schools.route("/EditTeacherClassPlan", methods=["POST"])
def EditTeacherClassPlan():
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

    idClassPlanReq = request.json.get('IdClassPlan')


    existingPlan = db.session.query(TeacherPlan).get(idClassPlanReq)
    
    if existingPlan is None:
        return 'Plano não contrado. Por favor, atualize a página', HttpCode.WARNING

    priceReq = request.json.get('Price')

    existingPlan.Price = priceReq

    db.session.commit()
    db.session.refresh(existingPlan)
    
    return jsonify({"EditPlan": existingPlan.to_json()}), HttpCode.SUCCESS


@bp_store_schools.route("/GetClassesInfo", methods=["POST"])
def GetClassesInfo():
    if not request.json:
        abort(HttpCode.ABORT)

    tokenReq = request.json.get('AccessToken')

    user = User.query.filter_by(AccessToken = tokenReq).first()

    if user is None:
        return "Sessão inválida, faça login novamente", HttpCode.EXPIRED_TOKEN
    
    stores = db.session.query(Store).filter(Store.IdCity == user.IdCity).all()

    schools = db.session.query(StoreSchool).filter(StoreSchool.IdStore.in_([store.IdStore for store in stores])).all()

    addedTeacherUserIds =[]
    teachersList = []

    schoolsList = []
    for school in schools:
        schoolsList.append(school.to_json_user())
        for teacher in school.Teachers:
            if teacher.IdUser not in addedTeacherUserIds:
                addedTeacherUserIds.append(teacher.IdUser)
                teachersList.append(teacher.to_json_user())
        
    return jsonify({"Schools": schoolsList, "Teachers": teachersList}), HttpCode.SUCCESS