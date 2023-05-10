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

#Rota utilizada por um funcionário quando ele clica no link pra confirmação do email, após criar a conta
@bp_employee.route("/EmailConfirmationEmployee", methods=["POST"])
def EmailConfirmationEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    emailConfirmationTokenReq = request.json.get('EmailConfirmationToken')
    employee = db.session.query(Employee).filter(Employee.EmailConfirmationToken == emailConfirmationTokenReq).first()
    
    if employee is None:
        return webResponse("Esse link não é válido", "Verifique se você acessou o mesmo link que enviamos ao seu e-mail. Caso contrário, fale com o nosso suporte."), HttpCode.WARNING

    if employee.EmailConfirmationDate is not None:
        return webResponse("Sua conta já foi validada!", "Faça login normalmente"), HttpCode.ALERT

    #Tudo ok com o token se chegou até aqui
    #Enviar e-mail avisando que estaremos verificando os dados da quadra e entraremos em contato em breve
    if employee.StoreOwner:
        sendEmail("O seu email já está confirmado! <br><br>Estamos conferindo os seus dados e estaremos entrando em contato em breve quando estiver tudo ok.<br><br>")

    #Salva a data de confirmação da conta do gestor
    employee.EmailConfirmationDate = datetime.now()
    db.session.commit()
    return "Email confirmado com sucesso", HttpCode.SUCCESS

#rota utilizada quando um funcionário clica em "esqueci minha senha"
@bp_employee.route('/ChangePasswordRequestEmployee', methods=['POST'])
def ChangePasswordRequestEmployee():
    if not request.json:
        abort(400)
    
    emailReq = request.json.get('Email')

    employee = db.session.query(Employee).filter(Employee.Email == emailReq).first()

    #verifica se o email já está cadastrado
    if employee is None:
        return webResponse("E-mail não cadastrado", None), HttpCode.WARNING

    #envia o email automático para redefinir a senha
    ### ver porque ele faz esse cálculo do datetime + email confirmation token, não poderia ser algo aleatorio?
    employee.ResetPasswordToken = str(datetime.now().timestamp()) + employee.EmailConfirmationToken
    db.session.commit()
    sendEmail("Troca de senha <br/> https://www.sandfriends.com.br/cgpw?str=1&tk="+employee.ResetPasswordToken)
    return webResponse("Link para troca de senha enviado", "Verifique sua caixa de e-mail e siga as instruções para trocar sua senha"), HttpCode.ALERT

#rota acessada quando o funcionario clica no link pra trocar a senha (para validar o token antes do funcionario digitar a nova senha)
@bp_employee.route('/ValidateChangePasswordTokenEmployee', methods=['POST'])
def ValidateChangePasswordTokenEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    changePasswordTokenReq = request.json.get('ChangePasswordToken')

    employee = Employee.query.filter_by(ResetPasswordToken=changePasswordTokenReq).first()
    
    if changePasswordTokenReq == 0 or changePasswordTokenReq is None or not employee:
        return webResponse("Esse link não é válido", "Verifique se você acessou o mesmo link que enviamos ao seu e-mail. Caso contrário, fale com o nosso suporte."), HttpCode.WARNING
    
    return "Token válido.", HttpCode.SUCCESS

#rota acessada para trocar a senha do funcionário
@bp_employee.route('/ChangePasswordEmployee', methods=['POST'])
def ChangePasswordEmployee():
    if not request.json:
        abort(400)

    resetPasswordTokenReq = request.json.get('ResetPasswordToken')
    newPassword = request.json.get('NewPassword')

    employee = db.session.query(Employee).filter(Employee.ResetPasswordToken == resetPasswordTokenReq).first()

    #verifica se o token está certo
    if employee is None:
        return webResponse("Esse link não é válido", "Verifique se você acessou o mesmo link que enviamos ao seu e-mail. Caso contrário, fale com o nosso suporte."), HttpCode.WARNING

    #adiciona a senha no banco de dados
    employee.Password = newPassword

    #anula o resetPasswordToken
    employee.ResetPasswordToken = None

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
    