from ..extensions import db
from datetime import datetime, timedelta
import json
from sqlalchemy.ext.hybrid import hybrid_property

class Match(db.Model):
    __tablename__ = 'match'
    IdMatch = db.Column(db.Integer, primary_key=True)
    Date = db.Column(db.DateTime)
    Cost = db.Column(db.Numeric(precision=10, scale=2))
    OpenUsers = db.Column(db.Boolean)
    MaxUsers = db.Column(db.Integer)
    Canceled = db.Column(db.Boolean)
    CreationDate = db.Column(db.DateTime)
    MatchUrl = db.Column(db.String(255))
    CreatorNotes = db.Column(db.String(255))
    IdRecurrentMatch = db.Column(db.Integer, db.ForeignKey('recurrent_match.IdRecurrentMatch'))

    Blocked = db.Column(db.Boolean)
    BlockedReason = db.Column(db.String(255))

    IdStoreCourt = db.Column(db.Integer, db.ForeignKey('store_court.IdStoreCourt'))
    StoreCourt = db.relationship('StoreCourt', foreign_keys = [IdStoreCourt])

    IdSport = db.Column(db.Integer, db.ForeignKey('sport.IdSport'))
    Sport = db.relationship('Sport', foreign_keys = [IdSport])

    #Horários da partida
    IdTimeBegin = db.Column(db.Integer, db.ForeignKey('available_hour.IdAvailableHour'))
    TimeBegin = db.relationship('AvailableHour', foreign_keys = [IdTimeBegin])
    IdTimeEnd = db.Column(db.Integer, db.ForeignKey('available_hour.IdAvailableHour'))
    TimeEnd = db.relationship('AvailableHour', foreign_keys = [IdTimeEnd])

    #Dados do Pagamento
    AsaasPaymentId = db.Column(db.String(45))
    AsaasBillingType = db.Column(db.String(45))
    AsaasPaymentStatus = db.Column(db.String(45))
    AsaasPixCode = db.Column(db.String(225))

    IdUserCreditCard = db.Column(db.Integer, db.ForeignKey('user_credit_card.IdUserCreditCard'))
    UserCreditCard = db.relationship('UserCreditCard', foreign_keys = [IdUserCreditCard])

    CostUser = db.Column(db.Numeric(precision=10, scale=2))
    CostFinal = db.Column(db.Numeric(precision=10, scale=2))
    CostAsaasTax = db.Column(db.Numeric(precision=10, scale=2)) 
    CostSandfriendsNetTax = db.Column(db.Numeric(precision=10, scale=2))
    AsaasSplit = db.Column(db.Numeric(precision=10, scale=2))

    #Cupom
    IdCoupon = db.Column(db.Integer, db.ForeignKey('coupon.IdCoupon'))
    Coupon = db.relationship('Coupon', foreign_keys = [IdCoupon])
    CostDiscount = db.Column(db.Numeric(precision=10, scale=2))

    @hybrid_property
    def paymentExpiration(self):
        return self.CreationDate + timedelta(minutes = 30)
    
    @hybrid_property
    def isPaymentExpired(self):
        return ((self.AsaasPaymentStatus == "PENDING") and (datetime.now() > self.paymentExpiration))
    
    Members = db.relationship('MatchMember', backref="Match")

    @hybrid_property
    def IsPaymentConfirmed(self):
        return self.AsaasPaymentStatus == "CONFIRMED"

    def MatchDatetime(self):
        return datetime.strptime(self.Date.strftime("%Y-%m-%d ") + self.TimeBegin.HourString, "%Y-%m-%d %H:%M")
    
    def MatchDuration(self):
        begin = datetime.strptime(self.TimeBegin.HourString, "%H:%M")
        end = datetime.strptime(self.TimeEnd.HourString, "%H:%M")
        #Calcula o número de horas entre os dois intervalos
        duration = (end - begin).total_seconds() / 3600
        return int(duration)

    def matchCreator(self):
        return [user for user in self.Members if user.IsMatchCreator][0]
    
    def IsFinished(self):
        return (self.MatchDatetime() < datetime.now())

    def to_json(self):
        if self.IdUserCreditCard is None:
            creditCard = None
        else:
            creditCard = self.UserCreditCard.to_json()
        if self.Coupon is None:
            coupon = None
        else:
            coupon = self.Coupon.to_json_min()
        
        return {
            'IdMatch': self.IdMatch,
            'StoreCourt': self.StoreCourt.to_json_match(),
            'IdSport': self.IdSport,
            'Date': self.Date.strftime("%Y-%m-%d"),
            'TimeBegin': self.IdTimeBegin,
            'TimeEnd': self.IdTimeEnd,
            'Cost': self.Cost,
            'OpenUsers': self.OpenUsers,
            'MaxUsers': self.MaxUsers,
            'Canceled': self.Canceled,
            'CreationDate': self.CreationDate.strftime("%Y-%m-%d"),
            'MatchUrl': self.MatchUrl,
            'CreatorNotes': self.CreatorNotes,
            'Members':[member.to_json() for member in self.Members],
            'PaymentStatus': self.AsaasPaymentStatus,
            'PaymentType': self.AsaasBillingType,
            'PixCode': self.AsaasPixCode,
            'CreditCard': creditCard,
            'PaymentExpirationDate': self.paymentExpiration.strftime("%Y-%m-%d %H:%M:%S"),
            'IdRecurrentMatch': self.IdRecurrentMatch,
            'CostFinal': self.CostFinal,
            'CostUser': self.CostUser ,
            'Coupon': coupon,
        }

    def to_json_open_match(self):
        members = [member.to_json() for member in self.Members if not(member.WaitingApproval) and not(member.Refused) and not(member.Quit) ]

        return {
            'IdMatch': self.IdMatch,
            'StoreCourt': self.StoreCourt.to_json_match(),
            'IdSport': self.IdSport,
            'Date': self.Date.strftime("%Y-%m-%d"),
            'TimeBegin': self.IdTimeBegin,
            'TimeEnd': self.IdTimeEnd,
            'Cost': self.Cost,
            'OpenUsers': self.OpenUsers,
            'MaxUsers': self.MaxUsers,
            'Canceled': self.Canceled,
            'CreationDate': self.CreationDate.strftime("%Y-%m-%d"),
            'MatchUrl': self.MatchUrl,
            'CreatorNotes': self.CreatorNotes,
            'IdRecurrentMatch': self.IdRecurrentMatch,
            'Members':members,
            'PaymentStatus': self.AsaasPaymentStatus,
            'PaymentType': self.AsaasBillingType,
            'PaymentExpirationDate': self.paymentExpiration.strftime("%Y-%m-%d %H:%M:%S"),
            'CostFinal': self.CostFinal,
            'CostUser': self.CostUser 
        }

    def to_json_min(self):
        #Retorna uma versão mais simplificada
        #Menos texto para transmitir para o app ao carregar a página
        #cuidado, esses nomes tem q ser vazios (caso de partida bloqueada, q não tem criador)
        matchCreatorFirstName = ""
        matchCreatorLastName = ""
        matchCreatorPhoto = None
        for member in self.Members:
            if member.IsMatchCreator == 1:
                if member.StorePlayer is not None:
                    matchCreatorFirstName = member.StorePlayer.FirstName
                    matchCreatorLastName = member.StorePlayer.LastName
                else:
                    matchCreatorFirstName = member.User.FirstName
                    matchCreatorLastName = member.User.LastName
                    if member.User.Photo is None:
                        matchCreatorPhoto = None
                    else:
                        matchCreatorPhoto = f"/img/usr/{member.User.Photo}.png"

        return {
            'IdMatch': self.IdMatch,            
            'CreationDate': self.CreationDate.strftime("%d/%m/%Y"),
            'Date': self.Date.strftime("%d/%m/%Y"),
            'TimeBegin': self.IdTimeBegin,
            'TimeEnd': self.IdTimeEnd,
            'StoreCourt': self.StoreCourt.to_json_match(),
            'Cost': self.Cost,
            'IdSport': self.IdSport,
            'CreatorNotes': self.CreatorNotes,
            'IdRecurrentMatch': self.IdRecurrentMatch,
            'matchCreatorFirstName': matchCreatorFirstName,
            'matchCreatorLastName': matchCreatorLastName,
            'matchCreatorPhoto': matchCreatorPhoto,
            'Blocked':self.Blocked,
            'BlockedReason':self.BlockedReason,
            'PaymentStatus': self.AsaasPaymentStatus,
            'PaymentType': self.AsaasBillingType,
            'PaymentExpirationDate': self.paymentExpiration.strftime("%Y-%m-%d %H:%M:%S"),
            'IdRecurrentMatch': self.IdRecurrentMatch,
            'CostFinal': self.CostFinal,
            'CostUser': self.CostUser 
        }
        