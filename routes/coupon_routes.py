from flask import Blueprint, jsonify, abort, request
from ..Models.coupon_model import Coupon
from ..extensions import db
from ..Models.http_codes import HttpCode
from datetime import datetime, timedelta
import string
import random

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

