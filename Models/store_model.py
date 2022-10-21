from ..extensions import db

class Store(db.Model):
    __tablename__ = 'store'
    IdStore = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(45))
    Address = db.Column(db.String(45))
    Latitude = db.Column(db.String(45))
    Longitude = db.Column(db.String(45))
    City = db.Column(db.Integer)
    Email = db.Column(db.String(45))
    PhoneNumber1 = db.Column(db.String(45))
    PhoneNumber2 = db.Column(db.String(45))
    Description = db.Column(db.String(250))
    Instagram = db.Column(db.String(100))

    
    def to_json(self):
        return {
            'IdStore': self.IdStore,
            'Name': self.Name,
            'Address': self.Address,
            'Latitude': self.Latitude,
            'Longitude': self.Longitude,
            'City': self.City,
            'Email': self.Email,
            'PhoneNumber1': self.PhoneNumber1,
            'PhoneNumber2': self.PhoneNumber2,
            'Logo': f"https://www.sandfriends.com.br/img/str/logo/{self.IdStore}.png",
            'Description': self.Description,
            'Instagram': self.Instagram,
        }