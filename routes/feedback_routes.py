from flask import Blueprint, jsonify, abort, request
from ..Models.feedback_model import Feedback
from ..Models.user_login_model import UserLogin
from ..extensions import db
from ..Models.http_codes import HttpCode

bp_feedback = Blueprint('bp_feedback', __name__)

@bp_feedback.route('/SendFeedback', methods=['POST'])
def SendFeedback():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessToken = request.json.get('accessToken')
    message = request.json.get('message')

    user = UserLogin.query.filter_by(AccessToken = accessToken).first()
    if user is None:
        return '1', HttpCode.INVALID_ACCESS_TOKEN

    newFeedback = Feedback(
        IdUser = user.IdUser,
        Message = message,
    )
    db.session.add(newFeedback)
    db.session.commit()
    return "ok", HttpCode.SUCCESS