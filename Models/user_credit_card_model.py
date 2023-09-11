from ..extensions import db
from datetime import datetime
from ..encryption import encrypt_aes, decrypt_aes
import os


class UserCreditCard(db.Model):
    __tablename__ = 'user_credit_card'
    IdUserCreditCard = db.Column(db.Integer, primary_key=True)
    Nickname = db.Column(db.String(45))
    CardNumber = db.Column(db.String(255))
    ExpirationDate = db.Column(db.DateTime)
    OwnerName = db.Column(db.String(45))
    OwnerCpf = db.Column(db.String(11))
    Deleted = db.Column(db.Boolean)
    Cep = db.Column(db.String(8))
    Address = db.Column(db.String(255))
    AddressNumber = db.Column(db.String(255))
    Issuer = db.Column(db.String(45))
    PhoneNumber = db.Column(db.String(45))

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    def to_json(self):
        return {
            'IdUserCreditCard': self.IdUserCreditCard,
            'CardNumber': decrypt_aes(self.CardNumber, os.environ['ENCRYPTION_KEY'])[-4:],
            'Nickname': self.Nickname,
            'ExpirationDate': self.ExpirationDate.strftime("%d/%m/%Y"),
            'Issuer': self.Issuer,
        }