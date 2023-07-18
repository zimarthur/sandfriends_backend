from flask import Blueprint, jsonify, abort, request
from datetime import datetime, timedelta, date
import bcrypt

from ..Models.user_model import User
from ..extensions import db
from ..Models.http_codes import HttpCode
from ..Models.user_credit_card_model import UserCreditCard

bp_user_credit_card = Blueprint('bp_user_credit_card', __name__)

#Adiciona um cartão de crédito de um usuário
@bp_user_credit_card.route('/AddUserCreditCard', methods=['POST'])
def AddUserCreditCard():
    if not request.json:
        abort(HttpCode.ABORT)

    accessTokenReq = request.json.get('AccessToken')
    cardNumberReq = request.json.get('CardNumber').encode('utf-8')
    cvvReq = request.json.get('CVV').encode('utf-8')
    nicknameReq = request.json.get('Nickname')
    expirationDateReq = request.json.get('ExpirationDate')
    ownerNameReq = request.json.get('OwnerName')
    ownerCpfReq = request.json.get('OwnerCpf')

    user = User.query.filter_by(AccessToken = accessTokenReq).first()
    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN
    
    #Caso o cartão já tenha sido cadastrado
    userCreditCards = db.session.query(UserCreditCard)\
        .filter(UserCreditCard.IdUser == user.IdUser)\
        .filter(UserCreditCard.LastDigits == cardNumberReq[-4:])\
        .filter(UserCreditCard.ExpirationDate == datetime.strptime(expirationDateReq, '%d/%m/%Y'))\
        .filter(UserCreditCard.Deleted == False).all()
    
    #Caso os últimos 4 dígitos e a data de validade sejam iguais, verifica as hashes
    for userCreditCard in userCreditCards:
        #Caso sejam cartões iguais
        if bcrypt.checkpw(cardNumberReq, (userCreditCard.CardNumber).encode('utf-8')):
            return "Você já cadastrou esse cartão",HttpCode.WARNING

    #Cadastra um cartão novo
    newUserCreditCard = UserCreditCard(
        IdUser = user.IdUser,
        CardNumber = bcrypt.hashpw(cardNumberReq, bcrypt.gensalt()),
        LastDigits = cardNumberReq[-4:],
        CVV = bcrypt.hashpw(cvvReq, bcrypt.gensalt()),
        Nickname = nicknameReq,
        ExpirationDate = datetime.strptime(expirationDateReq, '%d/%m/%Y'),
        OwnerName = ownerNameReq,
        OwnerCpf = ownerCpfReq,
        Deleted = False,
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