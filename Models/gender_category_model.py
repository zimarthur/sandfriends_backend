from ..extensions import db

class GenderCategory(db.Model):
    __tablename__ = 'gender_category'
    IdGenderCategory = db.Column(db.Integer, primary_key=True)
    GenderName = db.Column(db.String(45))

    def to_json(self):
        return {
            'IdGenderCategory': self.IdGenderCategory,
            'GenderName': self.GenderName,
        }