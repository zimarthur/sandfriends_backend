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

    IdMatch = db.Column(db.Integer, db.ForeignKey('match.IdMatch'))


    def to_json(self):
        return {
            'IdMatchMember': self.IdMatchMember,
            'IdUser': self.IdUser,
            'IsMatchCreator': self.IsMatchCreator,
            'WaitingApproval': self.WaitingApproval,
            'Refused': self.Refused,
            'IdMatch': self.IdMatch,
            'EntryDate': self.EntryDate,
            'QuitDate': self.QuitDate,
            'Quit': self.Quit
        }