from ..extensions import db

class Notification(db.Model):
    __tablename__ = 'notification'
    IdNotification = db.Column(db.Integer, primary_key=True)

    IdMatch = db.Column(db.Integer, db.ForeignKey('match.IdMatch'))
    Match = db.relationship('Match', foreign_keys = [IdMatch])

    IdNotificationCategory = db.Column(db.Integer, db.ForeignKey('notification_category.IdNotificationCategory'))
    NotificationCategory = db.relationship('NotificationCategory', foreign_keys = [IdNotificationCategory])

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    IdUserReplaceText = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    UserReplaceText = db.relationship('User', foreign_keys = [IdUserReplaceText])

    def to_json(self):
        return {
            'IdNotification': self.IdNotification,
            'Color':self.NotificationCategory.ColorString,
            'Message':self.NotificationCategory.Message.replace("{user}", self.UserReplaceText.FirstName),
            'Match': self.Match.to_json(),
        }