from flask import Blueprint, jsonify, abort, request
from ..Models.sport_model import Sport
from ..extensions import db

bp_sport = Blueprint('bp_sport', __name__)

@bp_sport.route('/GetSports', methods=['GET'])
def GetSports():
    sports = Sport.query.all()
    return jsonify([sport.to_json() for sport in sports])