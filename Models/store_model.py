from ..extensions import db

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
    HoursBeforeCancellation = db.Column(db.Integer)
    CNPJ = db.Column(db.String(14))
    CPF = db.Column(db.String(11))
    Neighbourhood = db.Column(db.String(50))
    CEP = db.Column(db.String(8))
    RegistrationDate = db.Column(db.DateTime)
    ApprovalDate = db.Column(db.DateTime)
    BankAccount = db.Column(db.String(45))
    Logo = db.Column(db.String(100))

    IdCity = db.Column(db.Integer, db.ForeignKey('city.IdCity'))
    City = db.relationship('City', foreign_keys = [IdCity])

    Courts = db.relationship('StoreCourt', backref="Store")
    Photos = db.relationship('StorePhoto', backref="Store")
    Employees = db.relationship('Employee', backref="Store")
        
    IsApproved = ApprovalDate != None
    
    def to_json(self):
        if self.Logo == None or self.Logo == "":
            logo = None
        else:
            logo = f"https://www.sandfriends.com.br/img/str/logo/{self.Logo}.png"
        
        return {
            'IdStore': self.IdStore,
            'Name': self.Name,
            'Address': self.Address,
            'AddressNumber': self.AddressNumber,
            'Latitude': self.Latitude,
            'Longitude': self.Longitude,
            'IdCity': self.IdCity,
            'City': self.City.to_json(),
            'HoursBeforeCancellation': self.HoursBeforeCancellation,
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
            'BankAccount': self.BankAccount
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
            'HoursBeforeCancellation': self.HoursBeforeCancellation,
            'PhoneNumber1': self.PhoneNumber1,
            'PhoneNumber2': self.PhoneNumber2,
            'Logo': f"https://www.sandfriends.com.br/img/str/logo/{self.Logo}.png",
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



    # def hasEmptyRequiredValues(storeReq,employeeReq):
    #     requiredFieldsStore = ["Name", "Address", "AddressNumber", "PhoneNumber1", "CEP", "Neighbourhood", "CPF"]
    #     requiredFieldsEmployee = ["Email", "FirstName", "LastName"]
        
    #     for field in requiredFieldsStore:
    #         if getattr(storeReq, field) is None or getattr(storeReq, field) == "":
    #             return True

    #     for field in requiredFieldsEmployee:
    #         if getattr(employeeReq, field) is None or getattr(employeeReq, field) == "":
    #             return True

    #     return False