from ..extensions import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'user'
    IdUser = db.Column(db.Integer, primary_key=True)

    FirstName = db.Column(db.String(50))
    LastName = db.Column(db.String(50))
    PhoneNumber = db.Column(db.String(12))
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


    Email = db.Column(db.String(255))
    Password = db.Column(db.String(255))
    AccessToken = db.Column(db.String(255))
    RegistrationDate = db.Column(db.DateTime)
    EmailConfirmationDate = db.Column(db.DateTime)
    EmailConfirmationToken = db.Column(db.String(300))
    ResetPasswordToken = db.Column(db.Integer)

    ThirdPartyLogin = db.Column(db.Boolean)
    AppleToken = db.Column(db.String(255))

    AllowNotifications = db.Column(db.Boolean)
    NotificationsToken = db.Column(db.String(255))
    AllowNotificationsOpenMatches = db.Column(db.Boolean)
    AllowNotificationsCoupons = db.Column(db.Boolean)

    AsaasId = db.Column(db.String(300))
    AsaasCreationDate = db.Column(db.DateTime)
    Cpf = db.Column(db.String(11))

    DateDisabled = db.Column(db.DateTime)

    IsTeacher = db.Column(db.Boolean)

    Ranks = db.relationship("UserRank", backref="User")
    TeacherSchools = db.relationship('StoreSchoolTeacher', back_populates="User")
    Teams = db.relationship('Team', back_populates="User")
    TeacherClassPlans = db.relationship('TeacherPlan', back_populates="User")

    def fullName(self):
        return self.FirstName+' '+self.LastName

    def to_json(self):
        if self.Birthday == None:
            birthday = None
        else:
            birthday = self.Birthday.strftime("%d/%m/%Y")
        
        if self.Photo == None or self.Photo == "":
            photo = None
        else:
            photo = f"/img/usr/{self.Photo}.png"
        
        rankList = []
        for rank in self.Ranks:
            rankList.append(rank.to_json())

        if self.GenderCategory == None:
            gender = None
        else:
            gender = self.GenderCategory.to_json()

        if self.SidePreferenceCategory == None:
            sidePreferenceCategory = None
        else:
            sidePreferenceCategory = self.SidePreferenceCategory.to_json()

        if self.IdSport == None:
            sport = None
        else:
            sport = self.Sport.to_json()

        if self.IdCity == None:
            city = None
        else:
            city = self.City.to_json()

        if self.DateDisabled is not None:
            dateDisabled = self.DateDisabled.strftime("%d/%m/%Y")
        else:
            dateDisabled = None

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
            'Sport': sport,
            'Ranks': rankList,
            'City': city,
            'Email': self.Email,
            'AccessToken': self.AccessToken,
            'RegistrationDate': self.RegistrationDate.strftime("%d/%m/%Y"),
            'EmailConfirmationDate': self.EmailConfirmationDate.strftime("%d/%m/%Y"),
            'EmailConfirmationToken': self.EmailConfirmationToken,
            'ThirdPartyLogin': self.ThirdPartyLogin,
            'ResetPasswordToken': self.ResetPasswordToken,
            'Cpf': self.Cpf,
            'DateDisabled': dateDisabled,
            'AllowNotifications': self.AllowNotifications,
            'NotificationsToken': self.NotificationsToken,
            'AllowNotificationsOpenMatches': self.AllowNotificationsOpenMatches,
            'AllowNotificationsCoupons': self.AllowNotificationsCoupons,
        }

    def to_json_web(self):
        idRank = None
        for rank in self.Ranks:
            if rank.RankCategory.IdSport == self.IdSport:
                idRank = rank.IdRankCategory

        if self.Photo == None:
            photo = None
        else:
            photo = f"/img/usr/{self.Photo}.png"
        return {
            'IdUser': self.IdUser,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'Photo': photo,
            'PhoneNumber': self.PhoneNumber,
            'IdGenderCategory': self.IdGenderCategory,
            'IdSport': self.IdSport,
            'IdRankCategory': idRank
        }

    def identification_to_json(self):
        if self.Photo == None:
            photo = None
        else:
            photo = f"/img/usr/{self.Photo}.png"
        return {
            'IdUser': self.IdUser,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'Photo': photo,
        }

    def identification_to_json_teacher(self):
        if self.Photo == None:
            photo = None
        else:
            photo = f"/img/usr/{self.Photo}.png"
        return {
            'IdUser': self.IdUser,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'Photo': photo,
            'PhoneNumber': self.PhoneNumber,
        }

    def to_json_teacher(self):
        if self.Photo == None:
            photo = None
        else:
            photo = f"/img/usr/{self.Photo}.png"
        return {
            'IdUser': self.IdUser,
            'FirstName': self.FirstName,
            'LastName': self.LastName,
            'Photo': photo,
            'PhoneNumber': self.PhoneNumber,
            'TeacherSchools':[teacherSchool.to_json_user() for teacherSchool in self.TeacherSchools],
            'Teams':[team.to_json_teacher() for team in self.Teams],
            'TeacherPlans':[teacherPlan.to_json() for teacherPlan in self.TeacherClassPlans],
        }