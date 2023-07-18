from ..extensions import db
from datetime import datetime


class UserCreditCard(db.Model):
    __tablename__ = 'user_credit_card'
    IdUserCreditCard = db.Column(db.Integer, primary_key=True)
    Nickname = db.Column(db.String(45))
    CardNumber = db.Column(db.String(255))
    LastDigits = db.Column(db.String(4))
    CVV = db.Column(db.String(255))
    ExpirationDate = db.Column(db.DateTime)
    OwnerName = db.Column(db.String(45))
    OwnerCpf = db.Column(db.String(11))
    Deleted = db.Column(db.Boolean)

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    def to_json(self):
        return {
            'IdUserCreditCard': self.IdUserCreditCard,
            'CardNumber': self.LastDigits,
            'Nickname': self.Nickname,
            'ExpirationDate': self.ExpirationDate.strftime("%d/%m/%Y"),
            'OwnerName': self.OwnerName,
            'OwnerCpf': self.OwnerCpf,
        }