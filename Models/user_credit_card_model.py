from ..extensions import db
from datetime import datetime


class UserCreditCard(db.Model):
    __tablename__ = 'user_credit_card'
    IdUserCreditCard = db.Column(db.Integer, primary_key=True)
    Nickname = db.Column(db.String(45))
    CardNumber = db.Column(db.String(16))
    cvv = db.Column(db.String(4))
    ExpirationDate = db.Column(db.DateTime)
    OwnerName = db.Column(db.String(45))
    OwnerCpf = db.Column(db.String(11))
    Deleted = db.Column(db.Boolean)
    Cep = db.Column(db.String(8))
    Address = db.Column(db.String(255))
    AddressNumber = db.Column(db.String(255))
    CreditCardToken = db.Column(db.String(255))
    AsaasPaymentId = db.Column(db.String(255))
    Issuer = db.Column(db.String(45))

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    def to_json(self):
        return {
            'IdUserCreditCard': self.IdUserCreditCard,
            'CardNumber': self.CardNumber,
            'Nickname': self.Nickname,
            'ExpirationDate': self.ExpirationDate.strftime("%d/%m/%Y"),
            'Issuer': self.Issuer,
        }