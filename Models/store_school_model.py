from ..extensions import db

class StoreSchool(db.Model):
    __tablename__ = 'store_school'
    IdStoreSchool = db.Column(db.Integer, primary_key=True)

    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))
    Store =  db.relationship('Store', back_populates = "Schools")

    Name = db.Column(db.String(45))
    IdSport = db.Column(db.Integer, db.ForeignKey('sport.IdSport'))
    CreationDate = db.Column(db.DateTime)
    Logo = db.Column(db.String(100))

    Teachers = db.relationship('StoreSchoolTeacher', back_populates="StoreSchool")

    @property
    def LogoUrl(self):
        if self.Logo == None or self.Logo == "":
            return self.Store.LogoUrl
        else:
            return f"/img/sch/{self.Logo}.png"

    def to_json(self):
        return {
            'IdStoreSchool': self.IdStoreSchool,
            'Name': self.Name,
            'IdSport': self.IdSport,
            'Name': self.Name,
            'CreationDate': self.CreationDate.strftime("%d/%m/%Y"),
            'Logo': self.LogoUrl,
            'StoreSchoolTeachers': [teacher.to_json() for teacher in self.Teachers],
        }

    def to_json_teacher(self):
        return {
            'IdStoreSchool': self.IdStoreSchool,
            'Name': self.Name,
            'IdSport': self.IdSport,
            'Name': self.Name,
            'CreationDate': self.CreationDate.strftime("%d/%m/%Y"),
            'Logo': self.LogoUrl,
        }

    def to_json_user(self):
        return {
            'IdStoreSchool': self.IdStoreSchool,
            'Name': self.Name,
            'IdSport': self.IdSport,
            'Name': self.Name,
            'CreationDate': self.CreationDate.strftime("%d/%m/%Y"),
            'Logo': self.LogoUrl,
            'Store': self.Store.to_json_user(),
        }