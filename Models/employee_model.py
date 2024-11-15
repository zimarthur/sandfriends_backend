from ..extensions import db
from datetime import datetime, timedelta, date
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy import or_
from ..Models.store_court_model import StoreCourt
from ..Models.store_model import Store

class Employee(db.Model):
    __tablename__ = 'employee'
    IdEmployee = db.Column(db.Integer, primary_key=True)
    FirstName = db.Column(db.String(45))
    LastName = db.Column(db.String(45))
    Email = db.Column(db.String(255))
    Password = db.Column(db.String(255))
    Admin = db.Column(db.Boolean)
    StoreOwner = db.Column(db.Boolean)
    RegistrationDate = db.Column(db.DateTime)
    EmailConfirmationDate = db.Column(db.DateTime)
    EmailConfirmationToken = db.Column(db.String(300))
    ResetPasswordToken = db.Column(db.String(300))
    DateDisabled = db.Column(db.DateTime)
    AccessToken = db.Column(db.String(255))
    AccessTokenApp = db.Column(db.String(255))
    LastAccessDate = db.Column(db.DateTime)
    AllowNotifications = db.Column(db.Boolean)
    NotificationsToken = db.Column(db.String(255))

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
            'AllowNotifications':self.AllowNotifications,
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
        daysToExpireToken = 7
        #Token expirado    
        if (datetime.now() - self.LastAccessDate).days > daysToExpireToken:
            return True
        #Token ok
        return False

#Verifica se algum dos AccessTokens (do site ou do app do gestor) é válido
def getEmployeeByToken(accessTokenReq):
    return db.session.query(Employee)\
        .filter(or_(Employee.AccessToken == accessTokenReq, Employee.AccessTokenApp == accessTokenReq)).first()

#Busca a loja a partir do token do employee
def getStoreByToken(accessTokenReq):
    return db.session.query(Store)\
        .join(Employee, Employee.IdStore == Store.IdStore)\
        .filter(or_(Employee.AccessToken == accessTokenReq, Employee.AccessTokenApp == accessTokenReq)).first()

#Busca a quadra a partir do token do employee
def getStoreCourtByToken(accessTokenReq, idStoreCourtReq):
    return db.session.query(StoreCourt)\
        .join(Employee, Employee.IdStore == StoreCourt.IdStore)\
        .filter(or_(Employee.AccessToken == accessTokenReq, Employee.AccessTokenApp == accessTokenReq))\
        .filter(StoreCourt.IdStoreCourt == idStoreCourtReq).first()