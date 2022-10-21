from ..extensions import db

class NotificationCategory(db.Model):
    __tablename__ = 'notification_category'
    IdNotificationCategory = db.Column(db.Integer, primary_key=True)
    Message = db.Column(db.Integer)
    ColorString = db.Column(db.Integer)

    def to_json(self):
        return {
            'IdNotificationCategory': self.IdNotificationCategory,
            'Message': self.Message,
            'ColorString': self.ColorString,
        }