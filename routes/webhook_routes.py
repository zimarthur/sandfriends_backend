from datetime import datetime
from flask import Blueprint, jsonify, abort, request, json

from sandfriends_backend.Models.notification_store_model import NotificationStore
from sandfriends_backend.emails import emailUserMatchConfirmed, emailUserRecurrentMatchConfirmed
from ..Models.http_codes import HttpCode
from ..extensions import db
from ..Models.match_model import Match
from ..Models.asaas_webhook_payments import AsaasWebhookPayments

bp_webhook = Blueprint('bp_webhook', __name__)

#Recebe um webhook do Asaas com informações de todos os pagamentos
@bp_webhook.route("/WebhookPayment", methods=["POST"])
def WebhookPayment():
    if not request.json:
        abort(HttpCode.ABORT)

    eventReq = request.json["event"]

    newAsaasWebhookPayment = AsaasWebhookPayments(
        Event = eventReq,
        AsaasPaymentId =request.json["payment"]["id"],
        RegistrationDatetime = datetime.now(),
    )
    db.session.add(newAsaasWebhookPayment)
    db.session.commit()

    #TODO: verificar o token da requisição para ser o access_token dos webhooks - fazer isso por segurança

    #se o evento
    if (eventReq == "PAYMENT_CONFIRMED") or (eventReq == "PAYMENT_RECEIVED"):
        #Verifica se existe uma partida com este payment_id
        payment_idReq = request.json["payment"]["id"]

        matches = Match.query.filter_by(AsaasPaymentId = payment_idReq).all()

        sendMatchEmail = False
        sendRecurrentMatchEmail = False
        for match in matches:
            if match.IsPaymentConfirmed == False:
                if match.IdRecurrentMatch == 0:
                    sendMatchEmail = True
                else:
                    sendRecurrentMatchEmail = True
                #Caso tenha, altera o status de pagamento dela
                match.AsaasPaymentStatus = "CONFIRMED"
                db.session.commit()

        if sendMatchEmail:
            #Notificação para a loja
            newNotificationStore = NotificationStore(
                IdUser = matches[0].matchCreator().IdUser,
                IdStore = matches[0].StoreCourt.IdStore,
                IdMatch = matches[0].IdMatch,
                IdNotificationStoreCategory = 1,
                EventDatetime = datetime.now()
            )
            db.session.add(newNotificationStore)
            db.session.commit()
            emailUserMatchConfirmed(matches[0])
        if sendRecurrentMatchEmail:
            #Notificação para a loja
            newNotificationStore = NotificationStore(
                IdUser = matches[0].matchCreator().IdUser,
                IdStore = matches[0].StoreCourt.IdStore,
                IdMatch = matches[0].IdMatch,
                IdNotificationStoreCategory = 3,
                EventDatetime = datetime.now()
            )
            db.session.add(newNotificationStore)
            db.session.commit()
            emailUserRecurrentMatchConfirmed(matches[0], request.json["payment"]["value"])
        

    return "ok", HttpCode.SUCCESS