from ..extensions import db

class TeacherPlan(db.Model):
    __tablename__ = 'teacher_plan'
    IdTeacherPlan = db.Column(db.Integer, primary_key=True)

    IdUser = db.Column(db.Integer, db.ForeignKey('user.IdUser'))

    ClassSize = db.Column(db.Integer)
    TimesPerWeek = db.Column(db.Integer)
    Price = db.Column(db.Integer)


    def to_json(self):
        return {
            'IdTeacherPlan': self.IdTeacherPlan,
            'ClassSize': self.ClassSize,
            'TimesPerWeek': self.TimesPerWeek,
            'Price': self.Price,
        }