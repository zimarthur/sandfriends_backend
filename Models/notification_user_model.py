from ..extensions import db

class NotificationUser(db.Model):
    __tablename__ = 'notification_user'
    IdNotificationUser = db.Column(db.Integer, primary_key=True)
    Seen = db.Column(db.Boolean)

    IdMatch = db.Column(db.Integer, db.ForeignKey('match.IdMatch'))
    Match = db.relationship('Match', foreign_keys = [IdMatch])

    IdNotificationUserCategory = db.Column(db.Integer, db.ForeignKey('notification_user_category.IdNotificationUserCategory'))
    NotificationUserCategory = db.relationship('NotificationUserCategory', foreign_keys = [IdNotificationUserCategory])

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    IdUserReplaceText = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    UserReplaceText = db.relationship('User', foreign_keys = [IdUserReplaceText])

    def to_json(self):
        return {
            'IdNotification': self.IdNotificationUser,
            'Color':self.NotificationUserCategory.ColorString,
            'Message':self.NotificationUserCategory.Message.replace("{user}", self.UserReplaceText.FirstName),
            'Match': self.Match.to_json(),
            'Seen':self.Seen,
            'User': self.UserReplaceText.to_json(),
        }