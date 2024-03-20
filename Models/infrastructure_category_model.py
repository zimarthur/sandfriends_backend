from ..extensions import db

class InfrastructureCategory(db.Model):
    __tablename__ = 'infrastructure_category'
    IdInfrastructureCategory = db.Column(db.Integer, primary_key=True)
    Description = db.Column(db.String(45))

    def to_json(self):
        return {
            'IdInfrastructureCategory': self.IdInfrastructureCategory,
            'Description': self.Description,
        }