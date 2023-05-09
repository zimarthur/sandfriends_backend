from flask import Blueprint, jsonify, abort, request
from flask_cors import cross_origin
from datetime import datetime, timedelta, date
from ..Models.store_model import Store
from ..extensions import db
from ..responses import webResponse
from ..Models.http_codes import HttpCode
from ..Models.city_model import City
from ..Models.state_model import State
from ..Models.sport_model import Sport
from ..Models.match_model import Match
from ..Models.employee_model import Employee
from ..Models.available_hour_model import AvailableHour
from ..Models.store_court_model import StoreCourt
from ..emails import sendEmail
from ..Models.store_access_token_model import EmployeeAccessToken
from ..access_token import EncodeToken, DecodeToken
from sqlalchemy import func

daysToExpireToken = 7

bp_employee = Blueprint('bp_employee', __name__)

@bp_employee.route('/EmployeeLogin', methods=['POST'])
def StoreLogin():
    if not request.json:
        abort(400)

    emailReq = request.json.get('Email')
    passwordReq = request.json.get('Password')

    employee = db.session.query(Employee).filter(Employee.Email == emailReq).first()

    if employee is None:
        return "Email não cadastrado", HttpCode.WARNING

    if employee.Password != passwordReq:
        return "Senha incorreta", HttpCode.WARNING

    #senha correta

    if employee.EmailConfirmationDate == None:
        return "A sua conta ainda não foi validada - Siga as instruções no seu e-mail", HttpCode.WARNING
    #email validado já

    if employee.Store.ApprovalDate == None:
        return "Estamos verificando as suas informações, entraremos em contato em breve", HttpCode.WAITING_APPROVAL
    #quadra já aprovada

    #Gera o AccessToken para os próximos logins
    currentDate = datetime.now()

    newEmployeeAccessToken = EmployeeAccessToken(
        IdEmployee = store.IdEmployee,
        AccessToken = EncodeToken(employee.IdEmployee),
        CreationDate = currentDate,
        LastAccessDate = currentDate
    )

    db.session.add(newEmployeeAccessToken)
    db.session.commit()

    #retorna as informações da quadra (esportes, horários, etc)
    return initStoreLoginData(store, newEmployeeAccessToken.AccessToken), HttpCode.SUCCESS


@bp_employee.route('/ValidateEmployeeAccessToken', methods=['POST'])
def ValidateEmployeeAccessToken():
    if not request.json:
        abort(400)
    
    receivedToken = request.json.get('AccessToken')

    employeeAccessToken = db.session.query(EmployeeAccessToken).filter(EmployeeAccessToken.AccessToken == receivedToken).first()

    #Caso não encontrar Token
    if employeeAccessToken is None:
        return "Token não encontrado", HttpCode.INVALID_ACCESS_TOKEN

    #Verificar se o Token é válido
    if (datetime.now() - employeeAccessToken.LastAccessDate).days > daysToExpireToken:
        return "Token expirado", HttpCode.INVALID_ACCESS_TOKEN

    #Token está válido - atualizar o LastAccessDate
    employeeAccessToken.LastAccessDate = datetime.now()
    db.session.commit()

    #Token válido - retorna as informações da quadra (esportes, horários, etc)
    return initStoreLoginData(employeeAccessToken.Store, employeeAccessToken.AccessToken), HttpCode.SUCCESS

@bp_employee.route('/ForgotPasswordStore', methods=['POST'])
def ForgotPasswordStore():
    if not request.json:
        abort(400)
    
    emailReq = request.json.get('Email')

    store = db.session.query(Store).filter(Store.Email == emailReq).first()

    #verifica se o email já está cadastrado
    if store is None:
        return "Email não cadastrado", HttpCode.EMAIL_NOT_FOUND
    #verifica se a loja já foi aprovada
    if store.ApprovalDate is None:
        return "Aguarde a verificação pela equipe do Sand Friends", HttpCode.WAITING_APPROVAL

    #envia o email automático para redefinir a senha
    ### ver porque ele faz esse cálculo do datetime + email confirmation token, não poderia ser algo aleatorio?
    store.ResetPasswordToken = str(datetime.now().timestamp()) + store.EmailConfirmationToken
    db.session.commit()
    sendEmail("Troca de senha <br/> https://www.sandfriends.com.br/redirect/?ct=cgpw&bd="+store.ResetPasswordToken)
    return 'Código enviado para redefinir a senha', HttpCode.SUCCESS

@bp_employee.route('/ChangePasswordStore', methods=['POST'])
def ChangePasswordStore():
    if not request.json:
        abort(400)

    resetPasswordTokenReq = request.json.get('ResetPasswordToken')
    newPassword = request.json.get('NewPassword')

    store = db.session.query(Store).filter(Store.ResetPasswordToken == resetPasswordTokenReq).first()

    #verifica se o token está certo
    if store is None:
        return "Token inválido", HttpCode.INVALID_RESET_PASSWORD_VALUE

    #adiciona a senha no banco de dados
    store.Password = newPassword

    #anula o resetPasswordToken
    store.ResetPasswordToken = None

    #anual os tokens de acesso
    #deixa a data de LastAccess deles como 10 ano atrás
    tokens = db.session.query(EmployeeAccessToken).filter(EmployeeAccessToken.IdStore == store.IdStore).all()
    for token in tokens:
        token.LastAccessDate = token.LastAccessDate - timedelta(days=10*365)
        
    db.session.commit()
    return 'Senha alterada com sucesso', HttpCode.SUCCESS

def initStoreLoginData(store, accessToken):
    startTime = datetime.now()
    #Lista com todos esportes
    sports = db.session.query(Sport).all()
    sportsList = []

    for sport in sports:
        sportsList.append(sport.to_json())

    #Lista com todas horas do dia
    hours = db.session.query(AvailableHour).all()
    hoursList = []

    for hour in hours:
        hoursList.append(hour.to_json())

    #Lista com as quadras do estabelecimento(json da quadra, esportes e preço)
    courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == store.IdStore).all()
    courtsList = []

    for court in courts:
        courtsList.append(court.to_json_full())

    matches = db.session.query(Match).filter(Match.IdStoreCourt.in_([court.IdStoreCourt for court in courts]))\
    .filter(Match.Date >= date(2023, 4, 1)).filter(Match.Date <= date(2023, 5, 30)).all()
    matchList =[]
    for match in matches:
        matchList.append(match.to_json())
    endTime =  datetime.now()
    return jsonify({'AccessToken':accessToken, 'Sports' : sportsList, 'AvailableHours' : hoursList, 'Store' : store.to_json(), 'Courts' : courtsList, 'Matches':matchList})

#Verifica se os dados que o estabelecimento forneceu estão completos (não nulos/vazios)
def storeHasEmptyValues(storeReq):
    if \
        storeReq.Name is None or\
        storeReq.Address is None or\
        storeReq.AddressNumber is None or\
        storeReq.Email is None or\
        storeReq.PhoneNumber1 is None or\
        storeReq.CEP is None or\
        storeReq.Neighbourhood is None or\
        storeReq.OwnerName is None or\
        storeReq.CPF is None:
        return True

    if \
        storeReq.Name == "" or\
        storeReq.Address == "" or\
        storeReq.AddressNumber == "" or\
        storeReq.Email == "" or\
        storeReq.PhoneNumber1 == "" or\
        storeReq.CEP == "" or\
        storeReq.Neighbourhood == "" or\
        storeReq.OwnerName == "" or\
        storeReq.CPF == "":
        return True
    return False
    