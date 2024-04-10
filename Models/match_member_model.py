from ..extensions import db

class MatchMember(db.Model):
    __tablename__ = 'match_member'
    IdMatchMember = db.Column(db.Integer, primary_key=True)
    IsMatchCreator = db.Column(db.Boolean)
    WaitingApproval = db.Column(db.Boolean)
    Refused = db.Column(db.Boolean)
    EntryDate = db.Column(db.DateTime)
    QuitDate = db.Column(db.DateTime)
    Quit = db.Column(db.Boolean, default=False)

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    IdStorePlayer = db.Column(db.Integer, db.ForeignKey('store_player.IdStorePlayer'))
    StorePlayer = db.relationship('StorePlayer', foreign_keys = [IdStorePlayer])

    IdMatch = db.Column(db.Integer, db.ForeignKey('match.IdMatch'))

    Cost = db.Column(db.Numeric(precision=10, scale=2))
    HasPaid = db.Column(db.Boolean, default=False)

    def isInMatch(self):
        return self.WaitingApproval == False and self.Refused == False and self.Quit == False

    def to_json(self):
        return {
            'IdMatchMember': self.IdMatchMember,
            'User': self.User.to_json(),
            'IsMatchCreator': self.IsMatchCreator,
            'WaitingApproval': self.WaitingApproval,
            'Refused': self.Refused,
            'IdMatch': self.IdMatch,
            'EntryDate': self.EntryDate,
            'QuitDate': self.QuitDate,
            'Quit': self.Quit,
            'HasPaid': self.HasPaid,
            'Cost': self.Cost,
        }