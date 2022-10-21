from ..extensions import db

class SidePreferenceCategory(db.Model):
    __tablename__ = 'side_preference_category'
    IdSidePreferenceCategory = db.Column(db.Integer, primary_key=True)
    SidePreferenceName = db.Column(db.String(45))

    def to_json(self):
        return {
            'IdSidePreferenceCategory': self.IdSidePreferenceCategory,
            'SidePreferenceName': self.SidePreferenceName,
        }