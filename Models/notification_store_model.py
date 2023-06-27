from ..extensions import db

class NotificationStore(db.Model):
    __tablename__ = 'notification_store'
    IdNotificationStore = db.Column(db.Integer, primary_key=True)
    EventDatetime = db.Column(db.DateTime)

    IdMatch = db.Column(db.Integer, db.ForeignKey('match.IdMatch'))
    Match = db.relationship('Match', foreign_keys = [IdMatch])

    IdNotificationStoreCategory = db.Column(db.Integer, db.ForeignKey('notification_store_category.IdNotificationStoreCategory'))
    NotificationStoreCategory = db.relationship('NotificationStoreCategory', foreign_keys = [IdNotificationStoreCategory])

    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))
    Store = db.relationship('Store', foreign_keys = [IdStore])

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))
    User = db.relationship('User', foreign_keys = [IdUser])

    def to_json(self):
        return {
            'IdNotificationStore': self.IdNotificationStore,
            'Message':self.NotificationStoreCategory.Message.replace("{user}", self.User.FirstName),
            'Match': self.Match.to_json_min(),
            'EventDatetime':self.EventDatetime.strftime("%d/%m/%Y %H:%M"),
        }