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

    Blocked = db.Column(db.Boolean)
    BlockedReason = db.Column(db.String(255))

    IdStoreCourt = db.Column(db.Integer, db.ForeignKey('store_court.IdStoreCourt'))
    StoreCourt = db.relationship('StoreCourt', foreign_keys = [IdStoreCourt])

    IdSport = db.Column(db.Integer, db.ForeignKey('sport.IdSport'))
    Sport = db.relationship('Sport', foreign_keys = [IdSport])

    IdTimeBegin = db.Column(db.Integer, db.ForeignKey('available_hour.IdAvailableHour'))
    TimeBegin = db.relationship('AvailableHour', foreign_keys = [IdTimeBegin])

    IdTimeEnd = db.Column(db.Integer, db.ForeignKey('available_hour.IdAvailableHour'))
    TimeEnd = db.relationship('AvailableHour', foreign_keys = [IdTimeEnd])

    Members = db.relationship('MatchMember', backref="Match")

    IsFinished = ((Date < datetime.today().date()) | ((Date == datetime.today().date()) & (IdTimeBegin < int(datetime.now().strftime("%H")))))

    def to_json(self):

        return {
            'IdMatch': self.IdMatch,
            'StoreCourt': self.StoreCourt.to_json_match(),
            'IdSport': self.IdSport,
            'Date': self.Date.strftime("%Y-%m-%d"),
            'TimeBegin': self.IdTimeBegin,
            'TimeEnd': self.IdTimeEnd,
            'Cost': int(self.Cost),
            'OpenUsers': self.OpenUsers,
            'MaxUsers': self.MaxUsers,
            'Canceled': self.Canceled,
            'CreationDate': self.CreationDate.strftime("%Y-%m-%d"),
            'MatchUrl': self.MatchUrl,
            'CreatorNotes': self.CreatorNotes,
            'Members':[member.to_json() for member in self.Members],
        }

    def to_json_open_match(self):
        members = [member.to_json() for member in self.Members if not(member.WaitingApproval) and not(member.Refused) and not(member.Quit) ]

        return {
            'IdMatch': self.IdMatch,
            'StoreCourt': self.StoreCourt.to_json_match(),
            'IdSport': self.IdSport,
            'Date': self.Date.strftime("%Y-%m-%d"),
            'TimeBegin': self.IdTimeBegin,
            'TimeEnd': self.IdTimeEnd,
            'Cost': int(self.Cost),
            'OpenUsers': self.OpenUsers,
            'MaxUsers': self.MaxUsers,
            'Canceled': self.Canceled,
            'CreationDate': self.CreationDate.strftime("%Y-%m-%d"),
            'MatchUrl': self.MatchUrl,
            'CreatorNotes': self.CreatorNotes,
            'Members':members,
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
            'TimeBegin': self.IdTimeBegin,
            'TimeEnd': self.IdTimeEnd,
            'IdStoreCourt': self.StoreCourt.IdStoreCourt,
            'Cost': int(self.Cost),
            'IdSport': self.IdSport,
            'CreatorNotes': self.CreatorNotes,
            'IdRecurrentMatch': self.IdRecurrentMatch,
            'MatchCreatorFirstName': MatchCreatorFirstName,
            'MatchCreatorLastName': MatchCreatorLastName,
            'MatchCreatorPhoto': MatchCreatorPhoto,
            'Blocked':self.Blocked,
            'BlockedReason':self.BlockedReason,
        }
        