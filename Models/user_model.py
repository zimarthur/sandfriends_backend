from ..extensions import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'user'
    IdUser = db.Column(db.Integer, db.ForeignKey('user_login.IdUser'), primary_key=True)
    UserLogin = db.relationship('UserLogin', foreign_keys = [IdUser])

    FirstName = db.Column(db.String(25))
    LastName = db.Column(db.String(25))
    PhoneNumber = db.Column(db.String(11))
    Birthday = db.Column(db.DateTime)
    Height = db.Column(db.Float)
    Photo = db.Column(db.String(100))

    IdGenderCategory = db.Column(db.Integer, db.ForeignKey('gender_category.IdGenderCategory'))
    GenderCategory = db.relationship('GenderCategory', foreign_keys = [IdGenderCategory])

    IdSidePreferenceCategory = db.Column(db.Integer, db.ForeignKey('side_preference_category.IdSidePreferenceCategory'))
    SidePreferenceCategory = db.relationship('SidePreferenceCategory', foreign_keys = [IdSidePreferenceCategory])

    IdCity = db.Column(db.Integer, db.ForeignKey('city.IdCity'))
    City = db.relationship('City', foreign_keys = [IdCity])

    IdSport = db.Column(db.Integer, db.ForeignKey('sport.IdSport'))
    Sport = db.relationship('Sport', foreign_keys = [IdSport])

    Ranks = db.relationship("UserRank", backref="User")

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
        
        rankList = []
        for rank in self.Ranks:
            rankList.append(rank.to_json())

        if self.GenderCategory == None:
            gender = None
        else:
            gender = self.GenderCategory.to_json(),

        if self.SidePreferenceCategory == None:
            sidePreferenceCategory = None
        else:
            sidePreferenceCategory = self.SidePreferenceCategory.to_json(),

        return {
            'IdUser': self.IdUser,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'PhoneNumber': self.PhoneNumber,
            'GenderCategory': gender,
            'Birthday': birthday,
            'Height': self.Height,
            'SidePreferenceCategory': sidePreferenceCategory,
            'Photo': photo,
            'Age':age,
            'Sport':self.Sport.to_json(),
            'Ranks':rankList,
            'Email': self.UserLogin.Email,
            'City': self.City.to_json(),
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