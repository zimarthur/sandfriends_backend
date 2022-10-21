from flask import current_app
from datetime import datetime
import jwt

def EncodeToken(idUser):
    try:
        payload = {
            'idUser': idUser,
            'time': str(datetime.now())
        }
        return jwt.encode(
            payload,
            current_app.config.get('SECRET_KEY'),
            algorithm='HS256'
        )
    except Exception as e:
        return e 

def DecodeToken(token):
    try:
        payload = jwt.decode(token, current_app.config.get('SECRET_KEY'), algorithms=['HS256'])['idUser']
        return payload
    except jwt.ExpiredSignatureError:
        return 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError:
        return 'Invalid token. Please log in again.'