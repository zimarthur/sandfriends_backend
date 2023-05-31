#$env:FLASK_APP="sandfriends_backend"
#$env:FLASK_ENV="development"  

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from .extensions import db
from .routes.user_login_routes import bp_user_login
from .routes.user_routes import bp_user
from .routes.store_routes import bp_store
from .routes.court_routes import bp_court
from .routes.match_routes import bp_match
from .routes.recurrent_match_routes import bp_recurrent_match
from .routes.sport_routes import bp_sport
from .routes.feedback_routes import bp_feedback
from .routes.debug_routes import bp_debug
from .routes.reward_routes import bp_reward
from .routes.employee_routes import bp_employee
from .routes.websites_routes import bp_websites

import json

with open('/etc/config.json') as config_file:
    config = json.load(config_file)
def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*", "methods": "*", "headers": "*"}})
    app.config['CORS_HEADERS'] = 'Content-Type'
    
    app.config['SECRET_KEY'] = config.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = config.get('SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.register_blueprint(bp_user_login)
    app.register_blueprint(bp_user)
    app.register_blueprint(bp_store)
    app.register_blueprint(bp_court)
    app.register_blueprint(bp_match)
    app.register_blueprint(bp_recurrent_match)
    app.register_blueprint(bp_sport)
    app.register_blueprint(bp_feedback)
    app.register_blueprint(bp_debug)
    app.register_blueprint(bp_reward)
    app.register_blueprint(bp_employee)
    app.register_blueprint(bp_websites)

    db.init_app(app)
    return app
