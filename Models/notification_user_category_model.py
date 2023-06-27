from ..extensions import db

class NotificationUserCategory(db.Model):
    __tablename__ = 'notification_user_category'
    IdNotificationUserCategory = db.Column(db.Integer, primary_key=True)
    Message = db.Column(db.String(255))
    ColorString = db.Column(db.String(45))

    def to_json(self):
        return {
            'IdNotificationCategory': self.IdNotificationUserCategory,
            'Message': self.Message,
            'ColorString': self.ColorString,
        }