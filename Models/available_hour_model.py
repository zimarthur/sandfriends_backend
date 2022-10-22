from ..extensions import db

class AvailableHour(db.Model):
    __tablename__ = 'available_hour'
    IdAvailableHour = db.Column(db.Integer, primary_key=True)
    HourString = db.Column(db.String(45))


    
    def to_json(self):
        return {
            'IdAvailableHour': self.IdAvailableHour,
            'HourString': self.HourString,
        }