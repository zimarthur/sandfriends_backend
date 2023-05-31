from flask import Blueprint, Flask, render_template

bp_websites = Blueprint('bp_websites', __name__)

@bp_websites.route('/login')
def index():
   return send_static_file('index.html')