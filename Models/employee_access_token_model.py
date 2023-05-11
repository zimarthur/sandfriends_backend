from ..extensions import db
from datetime import datetime, timedelta, date

class EmployeeAccessToken(db.Model):
    __tablename__ = 'employee_access_token'
    IdEmployeeAccessToken = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)

    IdEmployee = db.Column(db.Integer, db.ForeignKey('employee.IdEmployee'))
    Employee = db.relationship('Employee', foreign_keys = [IdEmployee])

    AccessToken = db.Column(db.String(225), nullable=False)
    CreationDate = db.Column(db.DateTime, nullable=False)
    LastAccessDate = db.Column(db.DateTime, nullable=False)
   
    def to_json(self):
        return {
            'IdEmployeeAccessToken': self.IdEmployeeAccessToken,
            'IdEmployee': self.IdEmployee,
            'AccessToken': self.AccessToken,
            'CreationDate': self.CreationDate,
            'LastAccessDate': self.LastAccessDate,
        }
    
    def isExpired(self, daysToExpireToken):
        #Token expirado    
        if (datetime.now() - self.LastAccessDate).days > daysToExpireToken:
            return False
        #Token ok
        return True