from ..extensions import db

class StoreInfrastructure(db.Model):
    __tablename__ = 'store_infrastructure'
    IdStoreInfrastructure = db.Column(db.Integer, primary_key=True)

    IdStore = db.Column(db.Integer, db.ForeignKey('store.IdStore'))

    IdInfrastructureCategory = db.Column(db.Integer, db.ForeignKey('infrastructure_category.IdInfrastructureCategory'))
    InfrastructureCategory = db.relationship('InfrastructureCategory', foreign_keys = [IdInfrastructureCategory])

    def to_json(self):
        return {
            'IdInfrastructureCategory': self.InfrastructureCategory.IdInfrastructureCategory,
            'Description': self.InfrastructureCategory.Description,
        }