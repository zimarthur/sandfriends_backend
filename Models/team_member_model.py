from ..extensions import db

class TeamMember(db.Model):
    __tablename__ = 'team_member'
    IdTeamMember = db.Column(db.Integer, primary_key=True)

    IdTeam = db.Column(db.Integer, db.ForeignKey('team.IdTeam'))

    #dono do time
    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))

    WaitingApproval = db.Column(db.Boolean)
    Refused = db.Column(db.Boolean)
    RequestDate = db.Column(db.DateTime)
    ResponseDate = db.Column(db.DateTime)

    def to_json(self):
        if self.ResponseDate is None:
            responseData = None
        else: 
            responseData = self.ResponseDate.strftime("%d/%m/%Y")
        return {
            'IdTeamMember': self.IdTeamMember,
            'IdUser': self.IdUser,
            'WaitingApproval': self.WaitingApproval,
            'Refused': self.Refused,
            'ResponseDate': responseData,
        }