from ..extensions import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'user'
    IdUser = db.Column(db.Integer, primary_key=True)
    FirstName = db.Column(db.String(25))
    LastName = db.Column(db.String(25))
    PhoneNumber = db.Column(db.String(11))
    IdGenderCategory = db.Column(db.Integer)
    Birthday = db.Column(db.DateTime)
    Height = db.Column(db.Float)
    IdSidePreferenceCategory = db.Column(db.Integer)
    Photo = db.Column(db.String(100))
    IdCity = db.Column(db.Integer)
    IdSport = db.Column(db.Integer)

    def to_json(self):
        if self.Birthday == None:
            birthday = None
            age = None
        else:
            birthday = self.Birthday.strftime("%d/%m/%Y")
            age = datetime.today().year - self.Birthday.year - ((datetime.today().month, datetime.today().day) < (self.Birthday.month, self.Birthday.day))
        if self.Photo == None:
            photo = None
        else:
            photo = f"https://www.sandfriends.com.br/img/usr/{self.Photo}.png"
        return {
            'IdUser': self.IdUser,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'PhoneNumber': self.PhoneNumber,
            'IdGenderCategory': self.IdGenderCategory,
            'Birthday': birthday,
            'Height': self.Height,
            'IdSidePreferenceCategory': self.IdSidePreferenceCategory,
            'Photo': photo,
            'Age':age,
            'IdCity':self.IdCity,
            'IdSport':self.IdSport
        }
    def identification_to_json(self):
        if self.Photo == None:
            photo = None
        else:
            photo = f"https://www.sandfriends.com.br/img/usr/{self.Photo}.png"
        return {
            'IdUser': self.IdUser,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'Photo': photo,
        }