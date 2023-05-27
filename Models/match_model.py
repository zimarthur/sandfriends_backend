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
    IdRecurrentMatch = db.Column(db.Integer, db.ForeignKey('recurrent_match.IdRecurrentMatch'))

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
            'StoreCourt': self.StoreCourt.to_json_match(),
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

    def to_json_open_match(self):
        members = [member.to_json() for member in self.Members if not(member.WaitingApproval) and not(member.Refused) and not(member.Quit) ]
        CanCancelUpTo = datetime.strptime(self.TimeBegin.HourString, '%H:%M').replace(year=self.Date.year,month=self.Date.month,day=self.Date.day) - timedelta(hours=self.StoreCourt.Store.HoursBeforeCancellation)

        return {
            'IdMatch': self.IdMatch,
            'StoreCourt': self.StoreCourt.to_json_match(),
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
            'Members':members,
            'CanCancelUpTo': CanCancelUpTo.strftime("%d/%m/%Y às %H:%M"),
        }

    def to_json_min(self):
        #Retorna uma versão mais simplificada
        #Menos texto para transmitir para o app ao carregar a página
        MatchCreatorFirstName = "Não encontrado"
        MatchCreatorLastName = ""
        MatchCreatorPhoto = None
        for member in self.Members:
            if member.IsMatchCreator == 1:
                MatchCreatorFirstName = member.User.FirstName
                MatchCreatorLastName = member.User.LastName
                if member.User.Photo is None:
                    MatchCreatorPhoto = None
                else:
                    MatchCreatorPhoto = f"https://www.sandfriends.com.br/img/usr/{member.User.Photo}.png"

        return {
            'IdMatch': self.IdMatch,            
            'CreationDate': self.CreationDate.strftime("%d/%m/%Y"),
            'Date': self.Date.strftime("%d/%m/%Y"),
            'TimeBegin': self.TimeBegin.IdAvailableHour,
            'TimeEnd': self.TimeEnd.IdAvailableHour,
            'IdStoreCourt': self.StoreCourt.IdStoreCourt,
            'Cost': int(self.Cost),
            'IdSport': self.IdSport,
            'CreatorNotes': self.CreatorNotes,
            'IdRecurrentMatch': self.IdRecurrentMatch,
            'MatchCreatorFirstName': MatchCreatorFirstName,
            'MatchCreatorLastName': MatchCreatorLastName,
            'MatchCreatorPhoto': MatchCreatorPhoto,
        }
        