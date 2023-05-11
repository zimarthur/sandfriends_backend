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
from ..Models.employee_access_token_model import EmployeeAccessToken
from ..access_token import EncodeToken, DecodeToken
from sqlalchemy import func

daysToExpireToken = 7

bp_employee = Blueprint('bp_employee', __name__)

#Rota utilizada para fazer login de qualquer employee no site
@bp_employee.route('/EmployeeLogin', methods=['POST'])
def StoreLogin():
    if not request.json:
        abort(HttpCode.ABORT)

    emailReq = request.json.get('Email')
    passwordReq = request.json.get('Password')

    employee = db.session.query(Employee).filter(Employee.Email == emailReq).first()

    if employee is None:
        return webResponse("Email não cadastrado", None), HttpCode.WARNING

    if employee.Password != passwordReq:
        return webResponse("Senha incorreta", None), HttpCode.WARNING

    #senha correta

    if employee.EmailConfirmationDate == None:
        return webResponse("Sua conta ainda não foi validada - Siga as instruções no seu e-mail", None), HttpCode.WARNING
    #email validado já

    if employee.Store.ApprovalDate == None:
        return webResponse("Estamos validando sua quadra, entraremos em contato em breve", None), HttpCode.ALERT
    #quadra já aprovada

    #Gera o AccessToken para os próximos logins
    currentDate = datetime.now()

    newEmployeeAccessToken = EmployeeAccessToken(
        IdEmployee = employee.IdEmployee,
        AccessToken = EncodeToken(employee.IdEmployee),
        CreationDate = currentDate,
        LastAccessDate = currentDate
    )

    db.session.add(newEmployeeAccessToken)
    db.session.commit()

    #retorna as informações da quadra (esportes, horários, etc)
    return initStoreLoginData(employee.Store, newEmployeeAccessToken.AccessToken), HttpCode.SUCCESS

#Rota utilizada para validar o AccessToken que fica no computador do usuário - para evitar fazer login com senha
@bp_employee.route('/ValidateEmployeeAccessToken', methods=['POST'])
def ValidateEmployeeAccessToken():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessTokenReq = request.json.get('AccessToken')

    employeeAccessToken = db.session.query(EmployeeAccessToken).filter(EmployeeAccessToken.AccessToken == accessTokenReq).first()

    #Caso não encontrar Token
    if employeeAccessToken is None:
        return webResponse("Token não encontrado", None), HttpCode.WARNING

    #Verificar se o Token é válido
    if (datetime.now() - employeeAccessToken.LastAccessDate).days > daysToExpireToken:
        return webResponse("Token expirado", None), HttpCode.WARNING

    #Token está válido - atualizar o LastAccessDate
    employeeAccessToken.LastAccessDate = datetime.now()
    db.session.commit()

    #Token válido - retorna as informações da quadra (esportes, horários, etc)
    return initStoreLoginData(employeeAccessToken.Employee.Store, employeeAccessToken.AccessToken), HttpCode.SUCCESS

#Rota utilizada por um admin para adicionar um novo funcionário
@bp_employee.route("/AddEmployee", methods=["POST"])
def AddEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    emailReq = (request.json.get('Email')).lower()
    
    employeeAccessToken = db.session.query(EmployeeAccessToken).filter(EmployeeAccessToken.AccessToken == accessTokenReq).first()
    
    #Verifica se o accessToken existe
    #Verifica se o accessToken do criador do usuário está expirado
    if (employeeAccessToken is None) or (not employeeAccessToken.isExpired(daysToExpireToken)):
        return webResponse("Ocorreu um erro", "Tente novamente, caso o problema persista, entre em contato com o nosso suporte"), HttpCode.WARNING

    #Verifica se quem está tentando criar um usuário é um Admin
    if not employeeAccessToken.Employee.Admin:
        return webResponse("Ops", "Você não tem permissões para criar usuários.\n\nApenas usuários administradores podem fazer isto."), HttpCode.WARNING

    #Usuário que será adicionado
    newEmployee = Employee(
        IdStore = employeeAccessToken.Employee.IdStore,
        Email = emailReq,
        Admin = False,
        StoreOwner = False,
        RegistrationDate = datetime.now()
    )

    #Verifica se este e-mail já pertence a um usuário
    alreadyUsed = db.session.query(Employee).filter(Employee.Email == newEmployee.Email).first()
    if alreadyUsed is not None:
        return webResponse("Ops", "Já existe um usuário com este e-mail"), HttpCode.WARNING

    db.session.add(newEmployee)
    db.session.commit()

    #enviar email para funcionário
    newEmployee.EmailConfirmationToken = str(datetime.now().timestamp()) + str(newEmployee.IdEmployee)
    db.session.commit()
    sendEmail("https://www.sandfriends.com.br/adem?tk="+newEmployee.EmailConfirmationToken)

    return webResponse("Tudo certo!", "Usuário adicionado com sucesso\n\nValide o novo usuário com o e-mail que acabamos de enviar"), HttpCode.SUCCESS

#Rota utilizada pelo novo funcionário para validar o link que ele clicou
@bp_employee.route("/ValidateNewEmployeeEmail", methods=["POST"])
def ValidateNewEmployeeEmail():
    if not request.json:
        abort(HttpCode.ABORT)

    emailConfirmationTokenReq = request.json.get('EmailConfirmationToken')

    newEmployee = db.session.query(Employee).filter(Employee.EmailConfirmationToken == emailConfirmationTokenReq).first()
    
    if newEmployee is None:
        return webResponse("Ocorreu um erro", "Tente novamente, caso o problema persista, entre em contato com o nosso suporte"), HttpCode.WARNING

    #Retornar o email e nome loja
    return {'Email': newEmployee.Email, 'StoreName': newEmployee.Store.Name}, HttpCode.SUCCESS

#Rota utilizada pelo novo funcionário, quando ele informa suas propriedades, tipo nome, sobrenome, senha
@bp_employee.route("/AddEmployeeInformation", methods=["POST"])
def AddEmployeeInformation():
    if not request.json:
        abort(HttpCode.ABORT)
    
    emailConfirmationTokenReq = request.json.get('EmailConfirmationToken')
    firstNameReq = (request.json.get('FirstName')).title()
    lastNameReq = (request.json.get('LastName')).title()
    passwordReq = request.json.get('Password')
    
    #Verifica o emailConfirmationToken
    newEmployee = db.session.query(Employee).filter(Employee.EmailConfirmationToken == emailConfirmationTokenReq).first()

    if newEmployee is None:
        return webResponse("Ocorreu um erro", "Tente novamente, caso o problema persista, entre em contato com o nosso suporte"), HttpCode.WARNING

    newEmployee.FirstName = firstNameReq
    newEmployee.LastName = lastNameReq
    newEmployee.Password = passwordReq

    #Confirma o e-mail do usuário
    #Zera o EmailConfirmationToken após a confirmação
    newEmployee.EmailConfirmationDate = datetime.now()
    newEmployee.EmailConfirmationToken = None
    db.session.commit()

    return webResponse("Tudo certo!", "Sua conta foi validada com sucesso"), HttpCode.ALERT

#Rota utilizada por um funcionário quando ele clica no link pra confirmação do email, após criar a conta
@bp_employee.route("/EmailConfirmationEmployee", methods=["POST"])
def EmailConfirmationEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    emailConfirmationTokenReq = request.json.get('EmailConfirmationToken')
    employee = db.session.query(Employee).filter(Employee.EmailConfirmationToken == emailConfirmationTokenReq).first()
    
    if employee is None:
        return webResponse("Esse link não é válido", "Verifique se você acessou o mesmo link que enviamos ao seu e-mail. Caso contrário, fale com o nosso suporte."), HttpCode.WARNING

    if employee.EmailConfirmationDate is not None and employee.Store.ApprovalDate is not None:
        return webResponse("Sua conta já foi validada!", "Faça login normalmente"), HttpCode.ALERT

    #Salva a data de confirmação da conta do gestor
    employee.EmailConfirmationDate = datetime.now()
    db.session.commit()
    return "Email confirmado com sucesso", HttpCode.SUCCESS

#Rota utilizada quando um funcionário clica em "esqueci minha senha"
@bp_employee.route('/ChangePasswordRequestEmployee', methods=['POST'])
def ChangePasswordRequestEmployee():
    if not request.json:
        abort(HttpCode.ABORT)
    
    emailReq = request.json.get('Email')

    employee = db.session.query(Employee).filter(Employee.Email == emailReq).first()

    #verifica se o email já está cadastrado
    if employee is None:
        return webResponse("E-mail não cadastrado", None), HttpCode.WARNING

    #envia o email automático para redefinir a senha
    employee.ResetPasswordToken = str(datetime.now().timestamp()) + str(employee.IdEmployee)
    db.session.commit()
    sendEmail("Troca de senha <br/> https://www.sandfriends.com.br/cgpw?str=1&tk="+employee.ResetPasswordToken)
    return webResponse("Link para troca de senha enviado!", "Verifique sua caixa de e-mail e siga as instruções para trocar sua senha"), HttpCode.ALERT

#Rota acessada quando o funcionario clica no link pra trocar a senha (para validar o token antes do funcionario digitar a nova senha)
@bp_employee.route('/ValidateChangePasswordTokenEmployee', methods=['POST'])
def ValidateChangePasswordTokenEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    resetPasswordTokenReq = request.json.get('ResetPasswordToken')

    employee = db.session.query(Employee).filter(Employee.ResetPasswordToken == resetPasswordTokenReq).first()
    
    if (resetPasswordTokenReq == 0) or (resetPasswordTokenReq is None) or (not employee):
        return webResponse("Esse link não é válido", "Verifique se você acessou o mesmo link que enviamos ao seu e-mail. Caso contrário, fale com o nosso suporte."), HttpCode.WARNING
    
    return "Token válido", HttpCode.SUCCESS

#Rota acessada para trocar a senha do funcionário
@bp_employee.route('/ChangePasswordEmployee', methods=['POST'])
def ChangePasswordEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    resetPasswordTokenReq = request.json.get('ResetPasswordToken')
    newPasswordReq = request.json.get('NewPassword')

    employeeReq = db.session.query(Employee).filter(Employee.ResetPasswordToken == resetPasswordTokenReq).first()

    #Verifica se o token está certo
    if (resetPasswordTokenReq == 0) or (resetPasswordTokenReq is None) or (not employeeReq):
        return webResponse("Esse link não é válido", "Verifique se você acessou o mesmo link que enviamos ao seu e-mail. Caso contrário, fale com o nosso suporte."), HttpCode.WARNING

    #Ddiciona a senha no banco de dados
    employeeReq.Password = newPasswordReq

    #Anula o changePasswordToken
    employeeReq.ResetPasswordToken = None

    #Anula os tokens de acesso
    #Deixa a data de LastAccess deles como 10 ano atrás
    tokens = db.session.query(EmployeeAccessToken).filter(EmployeeAccessToken.IdEmployee == employeeReq.IdEmployee).all()
    for token in tokens:
        token.LastAccessDate = token.LastAccessDate - timedelta(days=10*365)
        
    db.session.commit()
    return webResponse("Sua senha foi alterada!", None), HttpCode.ALERT

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
