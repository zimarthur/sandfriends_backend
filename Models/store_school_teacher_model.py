from ..extensions import db

class StoreSchoolTeacher(db.Model):
    __tablename__ = 'store_school_teacher'
    IdStoreSchoolTeacher = db.Column(db.Integer, primary_key=True)

    IdStoreSchool = db.Column(db.Integer, db.ForeignKey('store_school.IdStoreSchool'))

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    WaitingApproval = db.Column(db.Boolean)
    Refused = db.Column(db.Boolean)
    RequestDate = db.Column(db.DateTime)
    ResponseDate = db.Column(db.DateTime)

    def to_json(self):
        return {
            'IdStoreSchoolTeacher': self.IdStoreSchoolTeacher,
            'User': self.User.identification_to_json(),
            'WaitingApproval': self.WaitingApproval,
            'Refused': self.Refused,
            'ResponseDate': self.ResponseDate.strftime("%d/%m/%Y"),
        }