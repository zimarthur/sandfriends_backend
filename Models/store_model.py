from ..extensions import db
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import func

class Store(db.Model):
    __tablename__ = 'store'
    IdStore = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(50))
    Address = db.Column(db.String(50))
    AddressNumber = db.Column(db.String(50))
    Latitude = db.Column(db.String(50))
    Longitude = db.Column(db.String(50))
    PhoneNumber1 = db.Column(db.String(12))
    PhoneNumber2 = db.Column(db.String(12))
    Description = db.Column(db.String(350))
    Instagram = db.Column(db.String(100))
    CNPJ = db.Column(db.String(14))
    CPF = db.Column(db.String(11))
    Neighbourhood = db.Column(db.String(50))
    CEP = db.Column(db.String(8))
    RegistrationDate = db.Column(db.DateTime)
    ApprovalDate = db.Column(db.DateTime)
    Logo = db.Column(db.String(100))

    IdCity = db.Column(db.Integer, db.ForeignKey('city.IdCity'))
    City = db.relationship('City', foreign_keys = [IdCity])

    Courts = db.relationship('StoreCourt', backref="Store")
    Photos = db.relationship('StorePhoto', backref="Store")
    Employees = db.relationship('Employee', backref="Store")

    AsaasId = db.Column(db.String(255))
    AsaasWalletId = db.Column(db.String(255))
    AsaasApiKey = db.Column(db.String(255))

    CompanyType = db.Column(db.String(45))
    
    ### Taxas do Sandfriends
    FeeSandfriendsHigh = db.Column(db.Integer)
    FeeSandfriendsLow = db.Column(db.Integer)
    #Número de horas agendadas no mês para alterar da taxa alta para a baixa
    FeeThreshold = db.Column(db.Integer)

    #Forma como cobramos das quadras
    #PercentageFeesIncluded - Taxa do Sandfriends já inclui as taxas do Asaas
    #PercentageFeesNotIncluded - Taxa do Sandfriends não inclui taxas do Asaas
    #FixedPrice - Cobramos uma mensalidade fixa da quadra
    BillingMethod = db.Column(db.String(45))

    @property
    def IsAvailable(self):
        return self.ApprovalDate != None and self.Latitude != None and self.Longitude != None and self.Description != None and self.Logo != None and (len(self.Courts) > 0) and (len(self.Photos) > 1)
    
    @property
    def StoreOwner(self):
        for employee in self.Employees:
            if employee.StoreOwner:
                return employee

    def to_json(self):
        if self.Logo == None or self.Logo == "":
            logo = None
        else:
            logo = f"/img/str/logo/{self.Logo}.png"
        
        return {
            'IdStore': self.IdStore,
            'Name': self.Name,
            'Address': self.Address,
            'AddressNumber': self.AddressNumber,
            'Latitude': self.Latitude,
            'Longitude': self.Longitude,
            'IdCity': self.IdCity,
            'City': self.City.to_json(),
            'PhoneNumber1': self.PhoneNumber1,
            'PhoneNumber2': self.PhoneNumber2,
            'Logo': logo,
            'Description': self.Description,
            'Instagram': self.Instagram,
            'Cnpj': self.CNPJ,
            'Cep': self.CEP,
            'Neighbourhood': self.Neighbourhood,
            'Cpf': self.CPF,
            'ApprovalDate': self.ApprovalDate.strftime("%d/%m/%Y"),
            'StorePhotos':[photo.to_json() for photo in self.Photos if not(photo.Deleted)],
            'Courts':[court.to_json() for court in self.Courts],
            'Employees': [employee.to_json() for employee in self.Employees if employee.DateDisabled is None],
        }
    
    def to_json_match(self):
        return {
            'IdStore': self.IdStore,
            'Name': self.Name,
            'Address': self.Address,
            'AddressNumber': self.AddressNumber,
            'Latitude': self.Latitude,
            'Longitude': self.Longitude,
            'IdCity': self.IdCity,
            'City': self.City.to_json(),
            'PhoneNumber1': self.PhoneNumber1,
            'PhoneNumber2': self.PhoneNumber2,
            'Logo': f"/img/str/logo/{self.Logo}.png",
            'Description': self.Description,
            'Instagram': self.Instagram,
            'Cnpj': self.CNPJ,
            'Cep': self.CEP,
            'Neighbourhood': self.Neighbourhood,
            'Cpf': self.CPF,
            'ApprovalDate': self.ApprovalDate.strftime("%d/%m/%Y"),
            'StorePhotos':[photo.to_json() for photo in self.Photos if not(photo.Deleted)],
        }

    #Para a criação de uma quadra nova
    #Verifica se os dados que o estabelecimento forneceu estão completos (não nulos/vazios)
    def hasEmptyRequiredValues(self):
        requiredFields = ["Name", "Address", "AddressNumber", "PhoneNumber1", "CEP", "Neighbourhood", "CPF"]
        
        for field in requiredFields:
            if getattr(self, field) is None or getattr(self, field) == "":
                return True

        return False
