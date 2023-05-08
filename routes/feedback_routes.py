from flask import Blueprint, jsonify, abort, request
from ..Models.feedback_model import Feedback
from ..Models.user_model import User
from ..extensions import db
from ..Models.http_codes import HttpCode
from datetime import datetime

bp_feedback = Blueprint('bp_feedback', __name__)


#Rota utilizada para envio de avaliação pelos jogadores no app
@bp_feedback.route('/SendFeedback', methods=['POST'])
def SendFeedback():
    if not request.json:
        abort(HttpCode.ABORT)
    
    tokenReq = request.json.get('AccessToken')
    feedbackReq = request.json.get('Feedback')

    user = User.query.filter_by(AccessToken = tokenReq).first()
    if user is None:
        return 'token expirado', HttpCode.EXPIRED_TOKEN

    newFeedback = Feedback(
        IdUser = user.IdUser,
        Feedback = feedbackReq,
        RegistrationDate = datetime.now()
    )
    db.session.add(newFeedback)
    db.session.commit()
    return "Obrigado pelo seu comentário!", HttpCode.ALERT