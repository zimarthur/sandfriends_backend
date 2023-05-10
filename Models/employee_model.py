from ..extensions import db

class Employee(db.Model):
    __tablename__ = 'employee'
    IdEmployee = db.Column(db.Integer, primary_key=True)
    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))
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

    Store = db.relationship('Store', foreign_keys = [IdStore])
    
    def to_json(self):
        return {
            'IdEmployee': self.IdEmployee,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'Admin': self.Admin,
            'StoreOwner': self.StoreOwner,
            'EmailConfirmationDate': self.EmailConfirmationDate.strftime("%d/%m/%Y"),
            'DateDisabled': self.DateDisabled.strftime("%d/%m/%Y")
        }

    #Para a criação de uma quadra nova
    #Verifica se os dados que o estabelecimento forneceu estão completos (não nulos/vazios)
    def hasEmptyRequiredValues(self):
        requiredFields = ["Email", "FirstName", "LastName"]
        
        for field in requiredFields:
            if getattr(self, field) is None or getattr(self, field) == "":
                return True

        return False