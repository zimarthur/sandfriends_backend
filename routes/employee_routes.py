from flask import Blueprint, jsonify, abort, request
from flask_cors import cross_origin
from datetime import datetime, timedelta, date
from ..Models.store_model import Store
from ..Models.store_player_model import StorePlayer
from ..extensions import db
from ..utils import firstSundayOnNextMonth, lastSundayOnLastMonth, getFirstDayOfLastMonth
from ..responses import webResponse
from ..Models.http_codes import HttpCode
from ..Models.city_model import City
from ..Models.state_model import State
from ..Models.coupon_model import Coupon
from ..Models.sport_model import Sport
from ..Models.side_preference_category_model import SidePreferenceCategory
from ..Models.gender_category_model import GenderCategory
from ..Models.rank_category_model import RankCategory
from ..Models.match_model import Match, queryMatchesForCourts
from ..Models.match_member_model import MatchMember
from ..Models.reward_user_model import RewardUser
from ..Models.recurrent_match_model import RecurrentMatch
from ..Models.employee_model import Employee
from ..Models.available_hour_model import AvailableHour
from ..Models.store_court_model import StoreCourt
from ..Models.notification_store_model import NotificationStore
from ..Models.notification_store_category_model import NotificationStoreCategory
from ..emails import emailStoreChangePassword, emailStoreAddEmployee
from ..routes.store_player_routes import getStorePlayers
from ..access_token import EncodeToken, DecodeToken
from ..Models.employee_model import getEmployeeByToken
from sqlalchemy import func
import bcrypt
import json
import os

bp_employee = Blueprint('bp_employee', __name__)

#Rota utilizada para fazer login de qualquer employee no site
@bp_employee.route('/EmployeeLogin', methods=['POST'])
def EmployeeLogin():
    if not request.json:
        abort(HttpCode.ABORT)

    emailReq = request.json.get('Email')
    passwordReq = request.json.get('Password').encode('utf-8')
    isRequestFromAppReq = request.json.get('IsRequestFromApp')

    employee = db.session.query(Employee).filter(Employee.Email == emailReq).first()

    if employee is None:
        return webResponse("Não encontramos nenhuma quadra com este e-mail", "Se você é um jogador, realize o login diretamente pelo app"), HttpCode.WARNING

    if employee.DateDisabled is not None:
        return webResponse("Você não faz mais parte de nenhuma equipe",None), HttpCode.WARNING
    
    #if employee.Password != passwordReq:
    if not bcrypt.checkpw(passwordReq, (employee.Password).encode('utf-8')):
        return webResponse("Senha incorreta", None), HttpCode.WARNING

    #senha correta

    if employee.EmailConfirmationDate == None:
        return webResponse("Sua conta ainda não foi validada - Siga as instruções no seu e-mail", None), HttpCode.WARNING
    #email validado já

    if employee.Store.ApprovalDate == None:
        return webResponse("Estamos validando sua quadra, entraremos em contato em breve", None), HttpCode.ALERT
    #quadra já aprovada

    updateNotificationsReq = request.json.get('UpdateNotifications')
    allowNotificationsReq = request.json.get('AllowNotifications')
    notificationsTokenReq = request.json.get('NotificationsToken')

    if updateNotificationsReq:
        employee.AllowNotifications = allowNotificationsReq
    if notificationsTokenReq != "":
        employee.NotificationsToken = notificationsTokenReq

    #Define o novo AccessToken, com base em qual plataforma (app ou site) foi usada
    if isRequestFromAppReq:
        employee.AccessTokenApp = EncodeToken(employee.IdEmployee)
    else:
        employee.AccessToken = EncodeToken(employee.IdEmployee)

    employee.LastAccessDate = datetime.now()

    db.session.commit()

    #retorna as informações da quadra (esportes, horários, etc)
    return initStoreLoginData(employee, isRequestFromAppReq), HttpCode.SUCCESS

#Rota utilizada para validar o AccessToken que fica no computador do usuário - para evitar fazer login com senha
@bp_employee.route('/ValidateEmployeeAccessToken', methods=['POST'])
def ValidateEmployeeAccessToken():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessTokenReq = request.json.get('AccessToken')
    isRequestFromAppReq = request.json.get('IsRequestFromApp')

    employee = getEmployeeByToken(accessTokenReq)

    #Caso não encontrar Token
    if employee is None:
        return webResponse("Token não encontrado", None), HttpCode.EXPIRED_TOKEN

    #Verificar se o Token é válido
    if employee.isAccessTokenExpired():
        return webResponse("Token expirado", None), HttpCode.EXPIRED_TOKEN

    #Token está válido - atualizar o LastAccessDate
    employee.LastAccessDate = datetime.now()
    db.session.commit()

    #Token válido - retorna as informações da quadra (esportes, horários, etc)
    return initStoreLoginData(employee, isRequestFromAppReq), HttpCode.SUCCESS

#Rota utilizada por um admin para adicionar um novo funcionário
@bp_employee.route("/AddEmployee", methods=["POST"])
def AddEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    emailReq = (request.json.get('Email')).lower()
    
    employee = getEmployeeByToken(accessTokenReq)
    
    #Verifica se o accessToken existe
    #Verifica se o accessToken do criador do usuário está expirado
    if (employee is None) or employee.isAccessTokenExpired():
        return webResponse("Ocorreu um erro", "Tente novamente, caso o problema persista, entre em contato com o nosso suporte"), HttpCode.WARNING

    #Verifica se quem está tentando criar um usuário é um Admin
    if not employee.Admin:
        return webResponse("Ops", "Você não tem permissões para criar usuários.\n\nApenas usuários administradores podem fazer isto."), HttpCode.WARNING

    #Verifica se este e-mail já pertence a um usuário
    alreadyUsed = db.session.query(Employee).filter(Employee.Email == emailReq).first()
    if alreadyUsed is not None:
        return webResponse("Ops", "Já existe um usuário com este e-mail"), HttpCode.WARNING

    #Usuário que será adicionado
    newEmployee = Employee(
        IdStore = employee.IdStore,
        Email = emailReq,
        Admin = False,
        StoreOwner = False,
        RegistrationDate = datetime.now()
    )

    db.session.add(newEmployee)
    db.session.commit()

    #enviar email para funcionário
    newEmployee.EmailConfirmationToken = str(datetime.now().timestamp()) + str(newEmployee.IdEmployee)
    db.session.commit()
    emailStoreAddEmployee(newEmployee.Email, "https://" + os.environ['URL_QUADRAS'] + "/adem?tk="+newEmployee.EmailConfirmationToken)

    return returnStoreEmployees(employee.IdStore), HttpCode.SUCCESS

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
    passwordReq = request.json.get('Password').encode('utf-8')
    
    #Verifica o emailConfirmationToken
    newEmployee = db.session.query(Employee).filter(Employee.EmailConfirmationToken == emailConfirmationTokenReq).first()

    if newEmployee is None:
        return webResponse("Ocorreu um erro", "Tente novamente, caso o problema persista, entre em contato com o nosso suporte"), HttpCode.WARNING

    newEmployee.FirstName = firstNameReq
    newEmployee.LastName = lastNameReq
    newEmployee.Password = bcrypt.hashpw(passwordReq, bcrypt.gensalt())

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
    return "E-mail confirmado com sucesso", HttpCode.SUCCESS

@bp_employee.route("/SetEmployeeAdmin", methods=["POST"])
def SetEmployeeAdmin():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    idEmployeeReq = request.json.get('IdEmployee')
    isAdminReq = request.json.get('IsAdmin')
    
    employeeRequest = getEmployeeByToken(accessTokenReq)
    employeeChange = db.session.query(Employee).filter(Employee.IdEmployee == idEmployeeReq).first()

    #Verifica se o accessToken existe
    #Verifica se o accessToken do criador do usuário está expirado
    if (employeeRequest is None) or employeeRequest.isAccessTokenExpired():
        return webResponse("Ocorreu um erro", "Tente novamente, caso o problema persista, entre em contato com o nosso suporte"), HttpCode.WARNING

    #Verifica se quem está tentando criar um usuário é um Admin
    if not employeeRequest.Admin or employeeChange.StoreOwner:
        return webResponse("Ops", "Você não tem permissões para criar usuários.\n\nApenas usuários administradores podem fazer isto."), HttpCode.WARNING

    employeeChange.Admin = isAdminReq

    db.session.commit()

    return returnStoreEmployees(employeeRequest.IdStore), HttpCode.SUCCESS

@bp_employee.route("/RenameEmployee", methods=["POST"])
def RenameEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    firstNameReq = request.json.get('FirstName')
    lastNameReq = request.json.get('LastName')
    
    employee = getEmployeeByToken(accessTokenReq)

    #Verifica se o accessToken existe
    #Verifica se o accessToken do criador do usuário está expirado
    if (employee is None) or employee.isAccessTokenExpired():
        return webResponse("Ocorreu um erro", "Tente novamente, caso o problema persista, entre em contato com o nosso suporte"), HttpCode.WARNING

    employee.FirstName = firstNameReq
    employee.LastName = lastNameReq

    db.session.commit()

    return returnStoreEmployees(employee.IdStore), HttpCode.SUCCESS

@bp_employee.route("/RemoveEmployee", methods=["POST"])
def RemoveEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    idEmployeeReq = request.json.get('IdEmployee')
    isAdminReq = request.json.get('IsAdmin')
    
    employeeRequest = getEmployeeByToken(accessTokenReq)
    employeeChange = db.session.query(Employee).filter(Employee.IdEmployee == idEmployeeReq).first()

    #Verifica se o accessToken existe
    #Verifica se o accessToken do criador do usuário está expirado
    if (employeeRequest is None) or employeeRequest.isAccessTokenExpired():
        return webResponse("Ocorreu um erro", "Tente novamente, caso o problema persista, entre em contato com o nosso suporte"), HttpCode.WARNING

    #Verifica se quem está tentando remover um usuário é um Admin
    if not employeeRequest.Admin or employeeChange.StoreOwner:
        return webResponse("Ops", "Você não tem permissões para remover usuários.\n\nApenas usuários administradores podem fazer isto."), HttpCode.WARNING

    employeeChange.DateDisabled = datetime.now()

    db.session.commit()

    return returnStoreEmployees(employeeRequest.IdStore), HttpCode.SUCCESS

@bp_employee.route("/DeleteAccountEmployee", methods=["POST"])
def DeleteAccountEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    
    employee = getEmployeeByToken(accessTokenReq)

    #Verifica se o accessToken existe
    #Verifica se o accessToken do criador do usuário está expirado
    if (employee is None) or employee.isAccessTokenExpired():
        return webResponse("Ocorreu um erro", "Tente novamente, caso o problema persista, entre em contato com o nosso suporte"), HttpCode.WARNING

    employee.DateDisabled = datetime.now()

    db.session.commit()

    return webResponse("Sua conta foi deletada", "Se você deletou por engano, entre em contato com o suporte."), HttpCode.SUCCESS

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
    emailStoreChangePassword(employee.Email, employee.FirstName, "https://" + os.environ['URL_QUADRAS'] + "/cgpw?tk="+employee.ResetPasswordToken)

    return webResponse("Link para troca de senha enviado!", "Verifique sua caixa de e-mail e siga as instruções para trocar sua senha"), HttpCode.ALERT

#Rota acessada quando o funcionario clica no link pra trocar a senha (para validar o token antes do funcionario digitar a nova senha)
@bp_employee.route('/ValidateChangePasswordTokenEmployee', methods=['POST'])
def ValidateChangePasswordTokenEmployee():
    if not request.json:
        abort(HttpCode.ABORT)

    resetPasswordTokenReq = request.json.get('ChangePasswordToken')

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
    newPasswordReq = request.json.get('NewPassword').encode('utf-8')

    employeeReq = db.session.query(Employee).filter(Employee.ResetPasswordToken == resetPasswordTokenReq).first()

    #Verifica se o token está certo
    if (resetPasswordTokenReq == 0) or (resetPasswordTokenReq is None) or (not employeeReq):
        return webResponse("Esse link não é válido", "Verifique se você acessou o mesmo link que enviamos ao seu e-mail. Caso contrário, fale com o nosso suporte."), HttpCode.WARNING

    #Adiciona a senha no banco de dados
    employeeReq.Password = bcrypt.hashpw(newPasswordReq, bcrypt.gensalt())

    #Anula o changePasswordToken
    employeeReq.ResetPasswordToken = None

    #Anula os tokens de acesso
    #Deixa a data de LastAccess deles como 10 ano atrás
    tokens = db.session.query(Employee).filter(Employee.IdEmployee == employeeReq.IdEmployee).all()
    for token in tokens:
        if token.LastAccessDate is None:
            token.LastAccessDate = datetime.now() - timedelta(days=10*365)
        else:
            token.LastAccessDate = token.LastAccessDate - timedelta(days=10*365)
        
    db.session.commit()
    return webResponse("Sua senha foi alterada!", None), HttpCode.ALERT

#Rota acessada para trocar a senha do funcionário
@bp_employee.route('/UpdateMatchesList', methods=['POST'])
def UpdateMatchesList():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessTokenReq = request.json.get('AccessToken')

    employee = getEmployeeByToken(accessTokenReq)

    #Caso não encontrar Token
    if employee is None:
        return webResponse("Token não encontrado", None), HttpCode.EXPIRED_TOKEN

    #Verificar se o Token é válido
    if employee.isAccessTokenExpired():
        return webResponse("Token expirado", None), HttpCode.EXPIRED_TOKEN

    newDateReq = datetime.strptime(request.json.get('NewSelectedDate'), '%d/%m/%Y')

    startDate = lastSundayOnLastMonth(newDateReq)
    endDate = firstSundayOnNextMonth(newDateReq)

    courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == employee.Store.IdStore).all()

    matches = queryMatchesForCourts([court.IdStoreCourt for court in courts], startDate, endDate)
    
    matchList =[]
    for match in matches:
        matchList.append(match.to_json_min())

    return jsonify({'Matches':matchList, 'MatchesStartDate': startDate.strftime("%d/%m/%Y"), 'MatchesEndDate': endDate.strftime("%d/%m/%Y")}), HttpCode.SUCCESS

#Rota acessada para alterar permissão de notificações do app quadras
@bp_employee.route('/AllowNotificationsEmployee', methods=['POST'])
def AllowNotificationsEmployee():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessTokenReq = request.json.get('AccessToken')

    employee = getEmployeeByToken(accessTokenReq)

    #Caso não encontrar Token
    if employee is None:
        return webResponse("Token não encontrado", None), HttpCode.WARNING

    #Verificar se o Token é válido
    if employee.isAccessTokenExpired():
        return webResponse("Token expirado", None), HttpCode.WARNING

    allowNotificationsReq = request.json.get('AllowNotifications')
    notificationsTokenReq = request.json.get('NotificationsToken')
    
    employee.AllowNotifications = allowNotificationsReq
    employee.NotificationsToken = notificationsTokenReq

    db.session.commit()

    return jsonify({'AllowNotifications':allowNotificationsReq}), HttpCode.SUCCESS

def initStoreLoginData(employee, isRequestFromAppReq):

    store = employee.Store
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
    
    #Lista com todos os generos
    genders = db.session.query(GenderCategory).all()
    gendersList = []

    for gender in genders:
        gendersList.append(gender.to_json())
    
    #Lista com todos as categorias
    ranks = db.session.query(RankCategory).all()
    ranksList = []

    for rank in ranks:
        ranksList.append(rank.to_json())

    sidePreferences = db.session.query(SidePreferenceCategory).all()
    sidePreferencesList = []
    for sidePreference in sidePreferences:
        sidePreferencesList.append(sidePreference.to_json())

    #Lista com as quadras do estabelecimento(json da quadra, esportes e preço)
    courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == store.IdStore).all()
    courtsList = []

    for court in courts:
        courtsList.append(court.to_json_full())

    #query das partidas da loja. Pegar todas as partidas do mês atual contando a semana atual.
    #ex: se em um mês dia 31 fosse quarta, eu ainda preciso do resto da semana (quinta, sex, sab e dom), mesmo q sejam de outro mes
    startDate = lastSundayOnLastMonth(datetime.today())
    endDate = firstSundayOnNextMonth(datetime.today())

    matches = queryMatchesForCourts([court.IdStoreCourt for court in courts], startDate, endDate)

    matchList =[]
    for match in matches:
        matchList.append(match.to_json_min())

    recurrentMatches = db.session.query(RecurrentMatch).filter(RecurrentMatch.IdStoreCourt.in_([court.IdStoreCourt for court in courts]))\
                            .filter(RecurrentMatch.Canceled == False)\
                            .filter( RecurrentMatch.IsExpired == False).all()
    
    recurrentMatchList =[]
    for recurrentMatch in recurrentMatches:
        recurrentMatchList.append(recurrentMatch.to_json_store())

    rewards = db.session.query(RewardUser)\
                    .filter(RewardUser.IdStore == store.IdStore)\
                    .filter((RewardUser.RewardClaimedDate >= startDate) & (RewardUser.RewardClaimedDate <= endDate)).all()

    rewardsList = []
    for reward in rewards:
        rewardsList.append(reward.to_json_store())


    notifications = db.session.query(NotificationStore)\
                    .filter(NotificationStore.IdStore == store.IdStore)\
                    .order_by(NotificationStore.IdNotificationStore.desc()).limit(50)

    notificationList = []
    for notification in notifications:
        notificationList.append(notification.to_json())

    (storePlayersList, matchMembersList) = getStorePlayers(store)

    #Define qual AccessToken mandar com base em qual plataforma (app ou site) foi usada
    if isRequestFromAppReq:
        accessTokenReturn = employee.AccessTokenApp
    else:
        accessTokenReturn = employee.AccessToken

    couponsList = []
    coupons = db.session.query(Coupon)\
                .filter(Coupon.IdStoreValid == store.IdStore).all()

    for coupon in coupons:
        couponsList.append(coupon.to_json())

    return jsonify({'AccessToken': accessTokenReturn,\
                    'LoggedEmail': employee.Email,\
                    'Sports' : sportsList, \
                    'Hours' : hoursList,\
                    'Genders':gendersList,\
                    'Ranks': ranksList,\
                    'SidePreferences': sidePreferencesList, \
                    'Store' : store.to_json(),\
                    'Courts' : courtsList,\
                    'Matches':matchList,\
                    'MatchesStartDate': startDate.strftime("%d/%m/%Y"),\
                    'MatchesEndDate': endDate.strftime("%d/%m/%Y"),\
                    'RecurrentMatches': recurrentMatchList,\
                    'Rewards': rewardsList,\
                    'Notifications': notificationList,\
                    'StorePlayers': storePlayersList,\
                    'MatchMembers': matchMembersList,\
                    'Coupons': couponsList,\
                    })

def returnStoreEmployees(storeId):
    store = db.session.query(Store).filter(Store.IdStore == storeId).first()
    return jsonify({"Employees": [employee.to_json() for employee in store.Employees if employee.DateDisabled == None]})