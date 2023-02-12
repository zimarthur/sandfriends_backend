from ..extensions import db
from datetime import datetime, timedelta

class RecurrentMatch(db.Model):
    __tablename__ = 'recurrent_match'
    IdRecurrentMatch = db.Column(db.Integer, primary_key=True)
    CreationDate = db.Column(db.DateTime)
    LastPaymentDate = db.Column(db.DateTime)
    Weekday = db.Column(db.Integer)
    Canceled = db.Column(db.Boolean)

    IdTimeBegin = db.Column(db.Integer, db.ForeignKey('available_hour.IdAvailableHour'))
    TimeBegin = db.relationship('AvailableHour', foreign_keys = [IdTimeBegin])

    IdTimeEnd = db.Column(db.Integer, db.ForeignKey('available_hour.IdAvailableHour'))
    TimeEnd = db.relationship('AvailableHour', foreign_keys = [IdTimeEnd])

    IdStoreCourt = db.Column(db.Integer, db.ForeignKey('store_court.IdStoreCourt'))
    StoreCourt = db.relationship('StoreCourt', foreign_keys = [IdStoreCourt])

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    Matches = db.relationship('Match', backref="RecurrentMatch")

    def to_json(self):
        #conta partidas totais e pega partidas do mes
        recurrentMatchesCounter=0
        recurrentMatchesList=[]
        for match in self.Matches:
            if match.Canceled == False:
                recurrentMatchesCounter+=1
            if datetime.today().replace(day=1).date() <= match.Date:
                recurrentMatchesList.append(match.to_json())
        
        return {
            'IdRecurrentMatch': self.IdRecurrentMatch,
            'CreationDate': self.CreationDate.strftime("%Y-%m-%d"),
            'LastPaymentDate': self.LastPaymentDate.strftime("%Y-%m-%d"),
            'Weekday': self.Weekday,
            'TimeBegin': self.TimeBegin.HourString,
            'TimeEnd': self.TimeEnd.HourString,
            'Canceled': self.Canceled,
            'StoreCourt': self.StoreCourt.to_json(),
            'User': self.User.to_json(),
            'RecurrentMatchCounter':recurrentMatchesCounter,
            'NextRecurrentMatches': recurrentMatchesList,
        }
        