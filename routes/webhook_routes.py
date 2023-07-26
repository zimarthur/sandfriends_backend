from flask import Blueprint, jsonify, abort, request, json
from ..Models.http_codes import HttpCode
from ..extensions import db
from ..Models.match_model import Match

bp_webhook = Blueprint('bp_webhook', __name__)

#Recebe um webhook do Asaas com informações de todos os pagamentos
@bp_webhook.route("/WebhookPayment", methods=["POST"])
def WebhookPayment():
    if not request.json:
        abort(HttpCode.ABORT)

    #TODO: verificar o token da requisição para ser o access_token dos webhooks - fazer isso por segurança

    #Verifica se existe uma partida com este payment_id
    payment_idReq = request.json["payment"]["id"]

    match = Match.query.filter_by(AsaasPaymentId = payment_idReq).first()

    if match is None:
        return "Não encontramos nenhuma partida", HttpCode.SUCCESS

    #Caso tenha, altera o status de pagamento dela
    match.AsaasPaymentStatus = request.json["payment"]["status"]
    db.session.commit()

    #TODO: Enviar e-mail ao usuário

    return match.AsaasPaymentStatus, HttpCode.SUCCESS