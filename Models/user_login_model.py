from ..extensions import db

class UserLogin(db.Model):
    __tablename__ = 'user_login'
    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'), primary_key=True, autoincrement=True)
    User = db.relationship('User', foreign_keys = [IdUser])
    
    Email = db.Column(db.String(225), unique=True, nullable=False)
    Password = db.Column(db.String(225), nullable=False)
    AccessToken = db.Column(db.String(225), nullable=False)
    RegistrationDate = db.Column(db.DateTime, nullable=False)
    EmailConfirmationDate = db.Column(db.DateTime)
    EmailConfirmationToken = db.Column(db.String(100))
    ResetPasswordValue = db.Column(db.Integer)
    ThirdPartyLogin = db.Column(db.Boolean)
   

    def to_json(self):
        return {
            'IdUser': self.IdUser,
            'Email': self.Email,
            'Password': self.Password,
            'AccessToken': self.AccessToken,
            'RegistrationDate': self.RegistrationDate,
            'EmailConfirmationDate': self.EmailConfirmationDate,
            'EmailConfirmationToken': self.EmailConfirmationToken,
            'ThirdPartyLogin': self.ThirdPartyLogin,
            'ResetPasswordValue':self.ResetPasswordValue,
        }