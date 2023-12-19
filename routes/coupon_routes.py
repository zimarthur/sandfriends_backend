from flask import Blueprint, jsonify, abort, request
from ..Models.coupon_model import Coupon
from ..extensions import db
from ..Models.http_codes import HttpCode
from ..Models.store_model import Store
from ..Models.employee_model import getEmployeeByToken
from datetime import datetime, timedelta
import string
import random
from ..responses import webResponse
bp_coupon = Blueprint('bp_coupon', __name__)

#Verifica se o cupom de desconto é válido
#Se for válido, retorna o tipo (R$ ou %) e o valor do desconto
@bp_coupon.route('/ValidateCoupon', methods=['POST'])
def ValidateCoupon():
    if not request.json:
        abort(HttpCode.ABORT)

    codeReq = request.json.get('Code')
    idStoreReq = int(request.json.get('IdStore'))
    timeBeginReq = int(request.json.get('TimeBegin'))
    timeEndReq = int(request.json.get('TimeEnd'))
    matchDateReq = datetime.strptime(request.json.get('MatchDate'), '%d/%m/%Y')

    #Busca se o cupom existe e está válido
    coupon = db.session.query(Coupon)\
        .filter(Coupon.Code == codeReq)\
        .filter(Coupon.IdStoreValid == idStoreReq)\
        .filter(Coupon.IsValid == 1)\
        .filter((Coupon.IdTimeBeginValid <= timeBeginReq) & (Coupon.IdTimeEndValid >= timeEndReq))\
        .filter((Coupon.DateBeginValid <= matchDateReq) & (Coupon.DateEndValid >= matchDateReq))\
        .first()

    #Cupom não encontrado
    if coupon is None:
        return "Cupom inválido", HttpCode.WARNING

    #Cupom ok
    return coupon.to_json_min(), HttpCode.SUCCESS

def generateRandomCouponCode(length):
    #Gera uma série aleatória de caracteres
    characters = string.ascii_uppercase + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    
    #Verifica se ela já não existe
    coupon = Coupon.query.filter_by(Code = random_string).first()

    #Se o cupom for único
    if coupon is None:
        return random_string
    #Se já existir um cupom com esse código, roda de novo
    else:
        gerenateRandomCoupon(length)

@bp_coupon.route('/EnableDisableCoupon', methods=['POST'])
def EnableDisableCoupon():
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

    idCouponReq = request.json.get('IdCoupon')
    disableReq = request.json.get('Disable')

    coupon = db.session.query(Coupon)\
                .filter(Coupon.IdCoupon == idCouponReq)\
                .filter(Coupon.IdStoreValid == employee.IdStore).first()
    
    if coupon is None:
        return webResponse("Esse cupom não foi encontrato. Entre em contato com nossa equipe.",None), HttpCode.WARNING

    if disableReq:
        coupon.IsValid = False
    else:
        if coupon.DateEndValid < datetime.today().date():
            return webResponse("Não foi possível habilitar o cupom.","A validade deste cupom de desconto já foi expirada."), HttpCode.WARNING
        coupon.IsValid = True

    db.session.commit()

    return jsonify({'Coupon':coupon.to_json(),}), HttpCode.SUCCESS

    
