from ..extensions import db
from datetime import datetime, timedelta, date

daysToExpireToken = 7

class Employee(db.Model):
    __tablename__ = 'employee'
    IdEmployee = db.Column(db.Integer, primary_key=True)
    FirstName = db.Column(db.String(50))
    LastName = db.Column(db.String(50))
    Email = db.Column(db.String(255))
    Password = db.Column(db.String(255))
    Admin = db.Column(db.Boolean)
    StoreOwner = db.Column(db.Boolean)
    RegistrationDate = db.Column(db.DateTime)
    EmailConfirmationDate = db.Column(db.DateTime)
    EmailConfirmationToken = db.Column(db.String(300))
    ResetPasswordToken = db.Column(db.String(300))
    DateDisabled = db.Column(db.DateTime)
    AccessToken = db.Column(db.String(225), nullable=False)
    LastAccessDate = db.Column(db.DateTime, nullable=False)

    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))
    #Store = db.relationship('Store', foreign_keys = [IdStore])
    

    def to_json(self):
        if self.DateDisabled is not None:
            dateDisabled = self.DateDisabled.strftime("%d/%m/%Y")
        else:
            dateDisabled = None
        if self.EmailConfirmationDate is not None:
            emailConfirmationDate = self.EmailConfirmationDate.strftime("%d/%m/%Y")
        else:
            emailConfirmationDate = None
        return {
            'AccessToken': self.AccessToken,
            'IdEmployee': self.IdEmployee,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'Email': self.Email,
            'Admin': self.Admin,
            'StoreOwner': self.StoreOwner,
            'EmailConfirmationDate': emailConfirmationDate,
            'DateDisabled': dateDisabled,
        }

    #Para a criação de uma quadra nova
    #Verifica se os dados que o estabelecimento forneceu estão completos (não nulos/vazios)
    def hasEmptyRequiredValues(self):
        requiredFields = ["Email", "FirstName", "LastName"]
        
        for field in requiredFields:
            if getattr(self, field) is None or getattr(self, field) == "":
                return True

        return False

    def isAccessTokenExpired(self):
        #Token expirado    
        if (datetime.now() - self.LastAccessDate).days > daysToExpireToken:
            return False
        #Token ok
        return True