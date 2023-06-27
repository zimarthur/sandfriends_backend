from ..extensions import db

class NotificationStoreCategory(db.Model):
    __tablename__ = 'notification_store_category'
    IdNotificationStoreCategory = db.Column(db.Integer, primary_key=True)
    Message = db.Column(db.String(255))

    def to_json(self):
        return {
            'IdNotificationStoreCategory': self.IdNotificationStoreCategory,
            'Message': self.Message,
        }