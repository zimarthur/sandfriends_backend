from ..extensions import db
from datetime import datetime, timedelta

class Match(db.Model):
    __tablename__ = 'match'
    IdMatch = db.Column(db.Integer, primary_key=True)
    Date = db.Column(db.DateTime)
    Cost = db.Column(db.Integer)
    OpenUsers = db.Column(db.Boolean)
    MaxUsers = db.Column(db.Integer)
    Canceled = db.Column(db.Boolean)
    CreationDate = db.Column(db.DateTime)
    MatchUrl = db.Column(db.String(255))
    CreatorNotes = db.Column(db.String(255))

    IdStoreCourt = db.Column(db.Integer, db.ForeignKey('store_court.IdStoreCourt'))
    StoreCourt = db.relationship('StoreCourt', foreign_keys = [IdStoreCourt])

    IdSport = db.Column(db.Integer, db.ForeignKey('sport.IdSport'))
    Sport = db.relationship('Sport', foreign_keys = [IdSport])

    IdTimeBegin = db.Column(db.Integer, db.ForeignKey('available_hour.IdAvailableHour'))
    TimeBegin = db.relationship('AvailableHour', foreign_keys = [IdTimeBegin])

    IdTimeEnd = db.Column(db.Integer, db.ForeignKey('available_hour.IdAvailableHour'))
    TimeEnd = db.relationship('AvailableHour', foreign_keys = [IdTimeEnd])

    Members = db.relationship('MatchMember', backref="Match")

    def to_json(self):
        CanCancelUpTo = datetime.strptime(self.TimeBegin.HourString, '%H:%M').replace(year=self.Date.year,month=self.Date.month,day=self.Date.day) - timedelta(hours=self.StoreCourt.Store.HoursBeforeCancellation)

        return {
            'IdMatch': self.IdMatch,
            'StoreCourt': self.StoreCourt.to_json(),
            'Sport': self.Sport.to_json(),
            'Date': self.Date.strftime("%Y-%m-%d"),
            'TimeBegin': self.TimeBegin.HourString,
            'TimeEnd': self.TimeEnd.HourString,
            'TimeInteger': self.IdTimeBegin,
            'Cost': int(self.Cost),
            'OpenUsers': self.OpenUsers,
            'MaxUsers': self.MaxUsers,
            'Canceled': self.Canceled,
            'CreationDate': self.CreationDate.strftime("%Y-%m-%d"),
            'MatchUrl': self.MatchUrl,
            'CreatorNotes': self.CreatorNotes,
            'Members':[member.to_json() for member in self.Members],
            'CanCancelUpTo': CanCancelUpTo.strftime("%d/%m/%Y às %H:%M"),
        }
        