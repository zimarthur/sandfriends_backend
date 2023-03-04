#$env:FLASK_APP="sandfriends_backend"
#$env:FLASK_ENV="development"  

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from .extensions import db
from .routes.user_login_routes import bp_user_login
from .routes.user_routes import bp_user
from .routes.store_routes import bp_store
from .routes.match_routes import bp_match
from .routes.recurrent_match_routes import bp_recurrent_match
from .routes.store_photo_routes import bp_store_photo
from .routes.store_price_routes import bp_store_price
from .routes.sport_routes import bp_sport
from .routes.feedback_routes import bp_feedback
from .routes.debug_routes import bp_debug
from .routes.reward_routes import bp_reward

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
    app.register_blueprint(bp_match)
    app.register_blueprint(bp_recurrent_match)
    app.register_blueprint(bp_store_photo)
    app.register_blueprint(bp_store_price)
    app.register_blueprint(bp_sport)
    app.register_blueprint(bp_feedback)
    app.register_blueprint(bp_debug)
    app.register_blueprint(bp_reward)

    db.init_app(app)
    return app
