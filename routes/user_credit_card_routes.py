from flask import Blueprint, jsonify, abort, request
from datetime import datetime, timedelta, date

from ..Models.user_model import User
from ..extensions import db
from ..Models.http_codes import HttpCode
from ..Models.user_credit_card_model import UserCreditCard

from ..Asaas.Payment.create_payment import createPaymentPreAuthorization
from ..Asaas.Payment.refund_payment import refundPayment

bp_user_credit_card = Blueprint('bp_user_credit_card', __name__)

#Adiciona um cartão de crédito de um usuário
@bp_user_credit_card.route('/AddUserCreditCard', methods=['POST'])
def AddUserCreditCard():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    cardNumberReq = request.json.get('CardNumber')
    cvvReq = request.json.get('Cvv')
    nicknameReq = request.json.get('Nickname')
    expirationDateReq = request.json.get('ExpirationDate')
    ownerNameReq = request.json.get('OwnerName')
    ownerCpfReq = request.json.get('OwnerCpf')
    cepReq = request.json.get('Cep')
    addressReq = request.json.get('Address')
    addressNumberReq = request.json.get('AddressNumber')
    issuerReq = request.json.get('Issuer')

    expirationDate = datetime.strptime(expirationDateReq, "%m/%Y")

    user = User.query.filter_by(AccessToken = accessTokenReq).first()
    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN
    
    #Caso o cartão já tenha sido cadastrado
    userCreditCards = db.session.query(UserCreditCard)\
        .filter(UserCreditCard.IdUser == user.IdUser)\
        .filter(UserCreditCard.CardNumber == cardNumberReq)\
        .filter(UserCreditCard.ExpirationDate == datetime.strptime(expirationDateReq, '%m/%Y'))\
        .filter(UserCreditCard.Issuer == issuerReq)\
        .filter(UserCreditCard.Deleted == False).first()
    
    #Caso os últimos 4 dígitos e a data de validade sejam iguais, verifica as hashes
    if userCreditCards is not None:
        return "Este cartão já foi cadastrado anteriormente",HttpCode.ALERT

    # #Pré autorização no asaas
    # #Realiza uma cobrança de R$5 (mínimo do Asaas) pra ver se o cartão está válido e gerar o Token
    # authorizationResponse = createPaymentPreAuthorization(
    #     user= user,
    #     holderName= ownerNameReq,
    #     holderCpf= ownerCpfReq,
    #     cardNumber= cardNumberReq,
    #     cvv= cvvReq,
    #     expirationMonth= expirationDate.strftime("%m"),
    #     expirationYear= expirationDate.strftime("%Y"),
    #     addressNumber=addressNumberReq,
    #     cep=cepReq,
    # )
    
    # if authorizationResponse.status_code != 200:
    #     return "Não foi possível cadastrar seu cartão. Verifique se as informações estão corretas", HttpCode.WARNING

    # #Realiza o reembolso dos R$5 da validação do cartão
    # refundPayment(
    #     paymentId= authorizationResponse.json().get('id'),
    #     description= "Credit Card Authorization",
    # )

    #Cadastra um cartão novo
    newUserCreditCard = UserCreditCard(
        IdUser = user.IdUser,
        CardNumber = cardNumberReq,
        Cvv = cvvReq,
        Nickname = nicknameReq,
        ExpirationDate = datetime.strptime(expirationDateReq, '%m/%Y'),
        OwnerName = ownerNameReq,
        OwnerCpf = ownerCpfReq,
        Deleted = False,
        Cep = cepReq,
        Address = addressReq,
        AddressNumber = addressNumberReq,
        CreditCardToken = "awaiting asaas token",
        AsaasPaymentId = "awaiting asaas token",
        Issuer = issuerReq,
    )

    db.session.add(newUserCreditCard)

    db.session.commit()

    #Retorna a lista de cartões de créditos do usuário
    creditCards = db.session.query(UserCreditCard)\
            .filter(UserCreditCard.IdUser == user.IdUser)\
            .filter(UserCreditCard.Deleted == False).all()
    
    userCreditCardsList = []
    for creditCard in creditCards:
        userCreditCardsList.append(creditCard.to_json())

    return jsonify({'CreditCards': userCreditCardsList}), HttpCode.SUCCESS
    
@bp_user_credit_card.route('/DeleteUserCreditCard', methods=['POST'])
def DeleteUserCreditCard():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    idUserCreditCardReq = request.json.get('IdUserCreditCard')

    user = User.query.filter_by(AccessToken = accessTokenReq).first()
    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN

    creditCard = db.session.query(UserCreditCard)\
        .filter(UserCreditCard.IdUser == user.IdUser)\
        .filter(UserCreditCard.IdUserCreditCard == idUserCreditCardReq).first()
    
    if creditCard is None:
        return "Cartão não encontrado", HttpCode.ALERT
    
    creditCard.Deleted = True
    db.session.commit()

    creditCards = db.session.query(UserCreditCard)\
            .filter(UserCreditCard.IdUser == user.IdUser)\
            .filter(UserCreditCard.Deleted == False).all()
    
    userCreditCardsList = []
    for creditCard in creditCards:
        userCreditCardsList.append(creditCard.to_json())

    return jsonify({'CreditCards': userCreditCardsList}), HttpCode.SUCCESS