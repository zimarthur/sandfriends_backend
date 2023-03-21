from ..extensions import db

class Store(db.Model):
    __tablename__ = 'store'
    IdStore = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(45))
    Address = db.Column(db.String(45))
    Latitude = db.Column(db.String(45))
    Longitude = db.Column(db.String(45))
    PhoneNumber1 = db.Column(db.String(45))
    PhoneNumber2 = db.Column(db.String(45))
    Description = db.Column(db.String(250))
    Instagram = db.Column(db.String(100))
    HoursBeforeCancellation = db.Column(db.Integer)
    Email = db.Column(db.String(225))
    Password = db.Column(db.String(225))
    CNPJ = db.Column(db.String(14))
    CPF = db.Column(db.String(11))
    OwnerName = db.Column(db.String(225))
    Neighbourhood = db.Column(db.String(225))
    CEP = db.Column(db.String(8))
    RegistrationDate = db.Column(db.DateTime)
    EmailConfirmationDate = db.Column(db.DateTime)
    EmailConfirmationToken = db.Column(db.String(300))
    ApprovalDate = db.Column(db.DateTime)

    IdCity = db.Column(db.Integer, db.ForeignKey('city.IdCity'))
    City = db.relationship('City', foreign_keys = [IdCity])

    Courts = db.relationship('StoreCourt', backref="Store")
    Photos = db.relationship('StorePhoto', backref="Store")
    
    def to_json(self):
        return {
            'IdStore': self.IdStore,
            'Name': self.Name,
            'Address': self.Address,
            'Latitude': self.Latitude,
            'Longitude': self.Longitude,
            'IdCity': self.IdCity,
            'Email': self.Email,
            'HoursBeforeCancellation': self.HoursBeforeCancellation,
            'PhoneNumber1': self.PhoneNumber1,
            'PhoneNumber2': self.PhoneNumber2,
            'Logo': f"https://www.sandfriends.com.br/img/str/logo/{self.IdStore}.png",
            'Description': self.Description,
            'Instagram': self.Instagram,
            'StorePhotos':[photo.to_json() for photo in self.Photos]
        }