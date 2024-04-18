from ..extensions import db
from sqlalchemy.ext.hybrid import hybrid_property

class StoreSchoolTeacher(db.Model):
    __tablename__ = 'store_school_teacher'
    IdStoreSchoolTeacher = db.Column(db.Integer, primary_key=True)

    IdStoreSchool = db.Column(db.Integer, db.ForeignKey('store_school.IdStoreSchool'))
    StoreSchool =  db.relationship('StoreSchool', back_populates = "Teachers")

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    WaitingApproval = db.Column(db.Boolean)
    Refused = db.Column(db.Boolean)
    RequestDate = db.Column(db.DateTime)
    ResponseDate = db.Column(db.DateTime)

    @hybrid_property
    def Teams(self):
        return self.User.Teams

    def to_json(self):
        if self.ResponseDate is None:
            responseData = None
        else: 
            responseData = self.ResponseDate.strftime("%d/%m/%Y")
        return {
            'IdStoreSchoolTeacher': self.IdStoreSchoolTeacher,
            'User': self.User.identification_to_json(),
            'WaitingApproval': self.WaitingApproval,
            'Refused': self.Refused,
            'ResponseDate': responseData,
        }

    def to_json_user(self):
        if self.ResponseDate is None:
            responseData = None
        else: 
            responseData = self.ResponseDate.strftime("%d/%m/%Y")
        return {
            'IdStoreSchoolTeacher': self.IdStoreSchoolTeacher,
            'WaitingApproval': self.WaitingApproval,
            'Refused': self.Refused,
            'ResponseDate': responseData,
            'StoreSchool': self.StoreSchool.to_json_teacher(),
        }
    
    def to_json_teacher(self):
        if self.ResponseDate is None:
            responseData = None
        else: 
            responseData = self.ResponseDate.strftime("%d/%m/%Y")
        return {
            'IdStoreSchoolTeacher': self.IdStoreSchoolTeacher,
            'WaitingApproval': self.WaitingApproval,
            'Refused': self.Refused,
            'ResponseDate': responseData,
            'StoreSchool': self.StoreSchool.to_json_teacher(),
            'User': self.User.identification_to_json(),
        }