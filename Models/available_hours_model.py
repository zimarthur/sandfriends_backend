from ..extensions import db

class AvailableHours(db.Model):
    __tablename__ = 'available_hours'
    IdAvailableHours = db.Column(db.Integer, primary_key=True)
    HourString = db.Column(db.String(45))


    
    def to_json(self):
        return {
            'IdAvailableHours': self.IdAvailableHours,
            'HourString': self.HourString,
        }