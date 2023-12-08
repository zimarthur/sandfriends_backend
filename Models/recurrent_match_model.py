from ..extensions import db
from datetime import datetime, timedelta
from ..utils import getFirstDayOfLastMonth, isCurrentMonth
import json
from sqlalchemy.ext.hybrid import hybrid_property

  
class RecurrentMatch(db.Model):
    __tablename__ = 'recurrent_match'
    IdRecurrentMatch = db.Column(db.Integer, primary_key=True)
    Weekday = db.Column(db.Integer)
    Canceled = db.Column(db.Boolean)
    Blocked = db.Column(db.Boolean)
    BlockedReason = db.Column(db.String(255))
    CreationDate = db.Column(db.DateTime)
    LastPaymentDate = db.Column(db.DateTime)
    ValidUntil = db.Column(db.DateTime)

    IdTimeBegin = db.Column(db.Integer, db.ForeignKey('available_hour.IdAvailableHour'))
    TimeBegin = db.relationship('AvailableHour', foreign_keys = [IdTimeBegin])

    IdTimeEnd = db.Column(db.Integer, db.ForeignKey('available_hour.IdAvailableHour'))
    TimeEnd = db.relationship('AvailableHour', foreign_keys = [IdTimeEnd])

    IdStoreCourt = db.Column(db.Integer, db.ForeignKey('store_court.IdStoreCourt'))
    StoreCourt = db.relationship('StoreCourt', foreign_keys = [IdStoreCourt])

    IdSport = db.Column(db.Integer, db.ForeignKey('sport.IdSport'))
    Sport = db.relationship('Sport', foreign_keys = [IdSport])

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    IdStorePlayer = db.Column(db.Integer, db.ForeignKey('store_player.IdStorePlayer'))
    StorePlayer = db.relationship('StorePlayer', foreign_keys = [IdStorePlayer])

    Matches = db.relationship('Match', backref="RecurrentMatch")
    
    IsExpired = ((LastPaymentDate == CreationDate) & (datetime.today().replace(day=1).date() > CreationDate)) | \
               ((LastPaymentDate != CreationDate) & (LastPaymentDate < getFirstDayOfLastMonth()))

    @hybrid_property
    def isPaymentExpired(self):
        for match in self.Matches:
            if match.isPaymentExpired == True:
                return True
        return False
    
    def getCurrentMonthMatches(self):
        return [match.to_json_min() for match in self.Matches if isCurrentMonth(match.Date)]

    def getMatchCounter(self):
        recurrentMatchesCounter=0
        for match in self.Matches:
            if (match.Canceled == False) and (match.IsFinished() == True):
                recurrentMatchesCounter+=1

        return recurrentMatchesCounter
    
    def getNextRecurrentMatches(self):
        recurrentMatchesList=[]
        for match in self.Matches:
            if datetime.today().replace(day=1).date() <= match.Date:
                recurrentMatchesList.append(match.to_json())
        return recurrentMatchesList

    def to_json(self):
        return {
            'IdRecurrentMatch': self.IdRecurrentMatch,
            'CreationDate': self.CreationDate.strftime("%d/%m/%Y"),
            'LastPaymentDate': self.LastPaymentDate.strftime("%d/%m/%Y"),
            'Weekday': self.Weekday,
            'TimeBegin': self.TimeBegin.IdAvailableHour,
            'TimeEnd': self.TimeEnd.IdAvailableHour,
            'IdSport': self.IdSport,
            'Canceled': self.Canceled,
            'StoreCourt': self.StoreCourt.to_json_match(),
            'User': self.User.to_json(),
            'RecurrentMatchCounter':self.getMatchCounter(),
            'NextRecurrentMatches': self.getNextRecurrentMatches(),
            'ValidUntil': self.ValidUntil.strftime("%d/%m/%Y"),
        }

    def to_json_store(self):
        firstName = None
        lastName = None
        photo = None
        if self.User is not None:
            firstName = self.User.FirstName
            lastName = self.User.LastName
            if self.User.Photo is None:
                photo = None
            else:
                photo = f"/img/usr/{self.User.Photo}.png"
        elif self.StorePlayer is not None:
            firstName = self.StorePlayer.FirstName
            lastName = self.StorePlayer.LastName

        return {
            'IdRecurrentMatch': self.IdRecurrentMatch,
            'CreationDate': self.CreationDate.strftime("%d/%m/%Y"),
            'LastPaymentDate': self.LastPaymentDate.strftime("%d/%m/%Y"),
            'Weekday': self.Weekday,
            'TimeBegin': self.TimeBegin.IdAvailableHour,
            'TimeEnd': self.TimeEnd.IdAvailableHour,
            'IdStoreCourt': self.IdStoreCourt,
            'IdSport': self.IdSport,
            'UserFirstName': firstName,
            'UserLastName': lastName,
            'UserPhoto': photo,
            'RecurrentMatchCounter':self.getMatchCounter(),
            'Canceled': self.Canceled,
            'Blocked':self.Blocked,
            'BlockedReason':self.BlockedReason,
            'CurrentMonthMatches': self.getCurrentMonthMatches(),
        }