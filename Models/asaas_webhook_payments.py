from ..extensions import db

class AsaasWebhookPayments(db.Model):
    __tablename__ = 'asaas_webhook_payments'
    IdAsaasWebhookPayments = db.Column(db.Integer, primary_key=True)
    Event = db.Column(db.String(45))
    AsaasPaymentId = db.Column(db.String(45))
    RegistrationDatetime = db.Column(db.DateTime)