from ..extensions import db

class Sport(db.Model):
    __tablename__ = 'sport'
    IdSport = db.Column(db.Integer, primary_key=True)
    Description = db.Column(db.String(45)) 

    def to_json(self):
        return {
            'IdSport': self.IdSport,
            'Description': self.Description,
            'SportPhoto': f"https://www.sandfriends.com.br/img/spt/{self.IdSport}.png",
        }