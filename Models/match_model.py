from ..extensions import db

class Match(db.Model):
    __tablename__ = 'match'
    IdMatch = db.Column(db.Integer, primary_key=True)

    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))
    Store = db.relationship('Store', foreign_keys = [IdStore])

    IdStoreCourt = db.Column(db.Integer)
    IdSport = db.Column(db.Integer)
    Date = db.Column(db.DateTime)
    TimeBegin = db.Column(db.Integer)
    TimeEnd = db.Column(db.Integer)
    Cost = db.Column(db.Integer)
    OpenUsers = db.Column(db.Boolean)
    MaxUsers = db.Column(db.Integer)
    Canceled = db.Column(db.Boolean)
    CreationDate = db.Column(db.DateTime)
    MatchUrl = db.Column(db.String(255))
    CreatorNotes = db.Column(db.String(255))
    

    def to_json(self):
        # return {
        #     'IdMatch': self.IdMatch,
        #     'IdStore': self.IdStore,
        #     'IdStoreCourt': self.IdStoreCourt,
        #     'IdSport': self.IdSport,
        #     'Date': self.Date.strftime("%Y-%m-%d"),
        #     'TimeBegin': f"{self.TimeBegin}:00", #GAMBIARRA
        #     'TimeEnd': f"{self.TimeEnd}:00",
        #     'TimeInteger': self.TimeBegin,
        #     'Cost': int(self.Cost),
        #     'OpenUsers': self.OpenUsers,
        #     'MaxUsers': self.MaxUsers,
        #     'Canceled': self.Canceled,
        #     'CreationDate': self.CreationDate.strftime("%Y-%m-%d"),
        #     'MatchUrl': self.MatchUrl,
        #     'CreatorNotes': self.CreatorNotes,
        # }
        return {
            'Store': self.Store.Name,
        }