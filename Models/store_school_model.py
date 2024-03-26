from ..extensions import db

class StoreSchool(db.Model):
    __tablename__ = 'store_school'
    IdStoreSchool = db.Column(db.Integer, primary_key=True)
    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))
    Name = db.Column(db.String(45))
    IdSport = db.Column(db.Integer, db.ForeignKey('sport.IdSport'))
    CreationDate = db.Column(db.DateTime)
    Logo = db.Column(db.String(100))

    Teachers = db.relationship('StoreSchoolTeacher', backref="StoreSchool")

    def to_json(self):
        if self.Logo == None or self.Logo == "":
            logo = None
        else:
            logo = f"/img/sch/{self.Logo}.png"
        return {
            'IdStoreSchool': self.IdStoreSchool,
            'Name': self.Name,
            'IdSport': self.IdSport,
            'Name': self.Name,
            'CreationDate': self.CreationDate.strftime("%d/%m/%Y"),
            'Logo': logo,
            'StoreSchoolTeachers': [teacher.to_json() for teacher in self.Teachers],
        }