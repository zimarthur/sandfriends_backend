from ..extensions import db

class TeamMember(db.Model):
    __tablename__ = 'team_member'
    IdTeamMember = db.Column(db.Integer, primary_key=True)

    IdTeam = db.Column(db.Integer, db.ForeignKey('team.IdTeam'))
    Team =  db.relationship('Team', back_populates = "Members")

    #dono do time
    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

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
            'User': self.User.to_json_web(),
            'WaitingApproval': self.WaitingApproval,
            'Refused': self.Refused,
            'RequestDate': self.RequestDate.strftime("%d/%m/%Y"),
            'ResponseDate': responseData,
        }