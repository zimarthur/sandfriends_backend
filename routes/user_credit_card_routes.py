from flask import Blueprint, jsonify, abort, request
from datetime import datetime, timedelta, date

from ..Models.user_model import User
from ..extensions import db
from ..Models.http_codes import HttpCode
from ..Models.user_credit_card_model import UserCreditCard

from ..Asaas.Payment.create_payment import createPaymentPreAuthorization
from ..encryption import encrypt_aes, decrypt_aes
import os

bp_user_credit_card = Blueprint('bp_user_credit_card', __name__)

#Adiciona um cartão de crédito de um usuário
@bp_user_credit_card.route('/AddUserCreditCard', methods=['POST'])
def AddUserCreditCard():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    phoneNumberReq = request.json.get('PhoneNumber')
    cardNumberReq = request.json.get('CardNumber')
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

    #Cadastra um cartão novo
    newUserCreditCard = UserCreditCard(
        IdUser = user.IdUser,
        CardNumber = encrypt_aes(cardNumberReq, os.environ['ENCRYPTION_KEY']),
        Nickname = nicknameReq,
        ExpirationDate = datetime.strptime(expirationDateReq, '%m/%Y'),
        OwnerName = ownerNameReq,
        OwnerCpf = ownerCpfReq,
        Deleted = False,
        Cep = cepReq,
        Address = addressReq,
        AddressNumber = addressNumberReq,
        Issuer = issuerReq,
        PhoneNumber = phoneNumberReq,
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