from flask import Blueprint, jsonify, abort, request
import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging
from sandfriends_backend.utils import getFirstDayOfMonth, getLastDayOfMonth
from ..Models.feedback_model import Feedback
from ..Models.rank_category_model import RankCategory
from ..Models.user_rank_model import UserRank
from ..Models.user_model import User
from ..Models.store_model import Store
from ..Models.state_model import State
from ..Models.city_model import City
from ..Models.store_photo_model import StorePhoto
from ..Models.store_price_model import StorePrice
from ..Models.match_member_model import MatchMember
from ..Models.store_court_model import StoreCourt
from ..Models.store_court_sport_model import StoreCourtSport
from ..Models.match_model import Match
from ..Models.feedback_model import Feedback
from ..extensions import db
from ..Models.http_codes import HttpCode
from datetime import datetime, timedelta, date
from flask import Blueprint, jsonify, abort, request, json
from datetime import datetime, timedelta, date
from sqlalchemy import func, text
from ..extensions import db
import os
from ..responses import webResponse
import requests
from ..Asaas.asaas_base_api import asaas_api_key
from ..Models.http_codes import HttpCode
from ..Models.match_model import Match
from ..Models.recurrent_match_model import RecurrentMatch
from ..Models.user_model import User
from ..Models.user_rank_model import UserRank
from ..Models.rank_category_model import RankCategory
from ..Models.match_member_model import MatchMember
from ..Models.city_model import City
from ..Models.state_model import State
from ..Models.available_hour_model import AvailableHour
from ..Models.store_model import Store
from ..Models.store_price_model import StorePrice
from ..Models.store_photo_model import StorePhoto
from ..Models.store_court_model import StoreCourt
from ..Models.store_court_sport_model import StoreCourtSport
from ..Models.sport_model import Sport
from ..Models.reward_month_model import RewardMonth
from ..Models.employee_model import Employee
from ..Models.employee_model import getEmployeeByToken
from ..access_token import EncodeToken, DecodeToken
from sqlalchemy import or_

import json
from ..Asaas.asaas_base_api import requestPost
from .match_routes import GetAvailableCitiesList
from ..Asaas.Payment.create_payment import createPaymentPix, createPaymentCreditCard, getSplitPercentage
from ..emails import emailUserWelcomeConfirmationTest
from ..encryption import encrypt_aes, decrypt_aes
bp_debug = Blueprint('bp_debug', __name__)


def daterange(start_date, end_date):
    if start_date == end_date:
        yield start_date
    else:
        for n in range(int ((end_date - start_date).days)+1):
            yield start_date + timedelta(n)

def getHourIndex(hourString):
    return datetime.strptime(hourString, '%H:%M').hour

def getLastMonth():
    return (datetime.today().replace(day=1) - timedelta(days=1)).replace(day=1).date()

@bp_debug.route('/debug', methods=['POST'])
def debug():
    messageUser = messaging.Message(
        token= "fQ1nj4OSTcmHqLbAm_r-e2:APA91bGF0c45dnI6uN9ZPKq2nFvoWcP9388RjyyBuU9WzvvmK3mgsKYKXqFnfa0SGZ3bjFnr9UPSVHMsN6f2qTpMEdDQjAAyy_dTCCwIRb5YfWUr-ycrzd_Xo5okgXDetaanKP8t6Spi",
        notification=messaging.Notification(
            title='Pagamento aprovado!',
            body='Tudo certo para sua partida do dia ',
        ),
        data={
            "type": "match",
        }
    )
    responseUser = messaging.send(messageUser)
    # messageEmployees = messaging.MulticastMessage(
    #     notification=messaging.Notification(
    #         title='Pagamento aprovado!',
    #         body='Tudo certo para sua partida do dia ',
    #     ),
     
    #     tokens= [
    #         "fQ1nj4OSTcmHqLbAm_r-e2:APA91bGF0c45dnI6uN9ZPKq2nFvoWcP9388RjyyBuU9WzvvmK3mgsKYKXqFnfa0SGZ3bjFnr9UPSVHMsN6f2qTpMEdDQjAAyy_dTCCwIRb5YfWUr-ycrzd_Xo5okgXDetaanKP8t6Spi"
    #     ],
    # )
    # responseEmployees = messaging.send_multicast(messageEmployees)
    print('Successfully sent message to employees:', responseEmployees)
    return "OK", 200

    # idStoreReq = 1
    # #busca a quadra que vai ser feita a cobrança
    # store = db.session.query(Store)\
    #         .filter(Store.IdStore == idStoreReq).first()

    # value = 80
    # billingType = "CREDIT_CARD"

    # split = getSplitPercentage(store, value, billingType)
    
    # retorno = str(split)
    
    # return retorno, 200

    # idMatch = 1
    # partida = db.session.query(Match)\
    #         .filter(Match.IdMatch == idMatch).first()
    
    # inicio = datetime.strptime(partida.TimeBegin.HourString, "%H:%M")
    # fim = datetime.strptime(partida.TimeEnd.HourString, "%H:%M")
    # duration = (fim - inicio).total_seconds() / 3600

    # retorno = str(int(duration))
    
    # idStoreCourtReq = 1
    # #busca a quadra que vai ser feita a cobrança
    # store = db.session.query(Store)\
    #         .join(StoreCourt, StoreCourt.IdStore == Store.IdStore)\
    #         .filter(StoreCourt.IdStoreCourt == idStoreCourtReq).first()
    
    # numberOfCourts = db.session.query(StoreCourt)\
    #     .filter(StoreCourt.IdStore == store.IdStore).count()
    
    # currentMonthMatches = db.session.query(Match)\
    #     .filter(Match.IdStoreCourt.in_([court.IdStoreCourt for court in store.Courts]))\
    #     .filter(Match.Canceled == False)\
    #     .filter((Match.CreationDate >= getFirstDayOfMonth(datetime.now())) & (Match.CreationDate >= getLastDayOfMonth(datetime.now())) ).all()        
    
    # currentMonthMatchesHours=0
    # for match in currentMonthMatches:
    #     if match.isPaymentExpired == False:
    #         currentMonthMatchesHours += match.MatchDuration()

    # retorno = str(currentMonthMatchesHours)

    



    # password = "YourSecretPassword"
    # data_to_encrypt = "Senha"

    # encrypted_data = encrypt_aes(data_to_encrypt, password)
    # print(f"Encrypted: {encrypted_data}")

    # decrypted_data = decrypt_aes(encrypted_data+1, password)
    # print(f"Decrypted: {decrypted_data}")

    # return f"Decrypted: {decrypted_data}, Encrypted: {encrypted_data}", 200
    
    # emailUserWelcomeConfirmationTest("pedromilano902@gmail.com", "https://" + os.environ['URL_APP'] + "/redirect/?ct=emcf&bd=123123123")
    
    # return "E-mail enviado", 200

    #return jsonify({'Sports': "a",  "b":GetAvailableCitiesList()}), 200
    # newRecurrentMatch = RecurrentMatch(
    #         IdUser = 1,
    #         IdStoreCourt = 1,
    #         CreationDate = datetime.now(),
    #         Canceled = False,
    #         Weekday = 1,
    #         IdSport = 1,
    #         IdTimeBegin = 10,
    #         IdTimeEnd = 20,
    #         LastPaymentDate = datetime.now().date(),
    #         ValidUntil = datetime.now()
    #     )
    # db.session.add(newRecurrentMatch)
    # db.session.commit()
    #ambiente = os.environ['SQLALCHEMY_DATABASE_URI']
    #ambiente = os.environ['SQLALCHEMY_DATABASE_URI']

    #return ambiente, 200
    # newReward = RewardMonth(
    #     StartingDate = getFirstDayOfMonth(datetime.now()),
    #     EndingDate = getLastDayOfMonth(datetime.now()),
    #     NTimesToReward = 4,
    #     IdRewardCategory = 1,
    # )
    # db.session.add(newReward)
    # db.session.commit()
    # db.session.refresh(newReward)
    # #reward = db.session.query(RewardMonth).first()

    # return jsonify({'reward': newReward.to_json()}), 200
    # URL = URL_list.get('URL_QUADRAS')
    # return URL, 200

    #store = db.session.query(Store).first()
    #return str(store.IsAvailable), 200
    # stores = db.session.query(Store).filter(Store.IsAvailable >= 1).all()
    # a=[]
    # for store in stores:
    #     a.append(store.Name)
    # return jsonify({"a": a}), HttpCode.SUCCESS
    
    # firstDayOfMonth = datetime.today().replace(day = 1, month = 6)
    # return str(firstDayOfMonth - timedelta(days=(firstDayOfMonth.weekday()))), 200
    # return webResponse("Você está quase lá!", \
    # "Para concluir seu cadastro, é necessário que você valide seu e-mail.\nAcesse o link que enviamos e sua conta será criada.\n\n\Se tiver qualquer dúvida, é só nos chamar, ok?"), HttpCode.ALERT
    # logins = db.session.query(EmployeeAccessToken).all()
    # loginList  =[]
    # for login in logins:
    #     loginList.append(login.to_json())
    # return jsonify({"test": loginList}), 200 
    #IdMatchdReq = request.json.get('IdMatch')

    #partida = db.session.query(Match).filter(Match.IdMatch == IdMatchdReq).first()

    #return partida.to_json_min()

    # courts =[1,2]
    # start_date = date(2023, 3, 9)
    # end_date = date(2023, 5, 9)
    # for court in courts: 
    #     for single_date in daterange(start_date, end_date):
    #         for time in range(10,20):
    #             newMatch = Match(
    #                     IdStoreCourt = court,
    #                     IdSport = 1,
    #                     Date = single_date,
    #                     IdTimeBegin = time,
    #                     IdTimeEnd = time+1,
    #                     Cost = 90,
    #                     OpenUsers = False,
    #                     MaxUsers = 0,
    #                     Canceled = False,
    #                     CreationDate = datetime.now(),
    #                     CreatorNotes = "",
    #                     IdRecurrentMatch = 0,
    #                 )
    #             db.session.add(newMatch)
    #             db.session.commit()
    #             newMatch.MatchUrl = f'{newMatch.IdMatch}{int(round(newMatch.CreationDate.timestamp()))}'
    #             db.session.commit()
    #             matchMember = MatchMember(
    #                 IdUser = 2,
    #                 IsMatchCreator = True,
    #                 WaitingApproval = False,
    #                 Refused = False,
    #                 IdMatch = newMatch.IdMatch,
    #                 Quit = False,
    #                 EntryDate = datetime.now(),
    #             )
    #             db.session.add(matchMember)
    #             db.session.commit()


    # IdUserReq = request.json.get('IdUser')
    # FirstNameReq = request.json.get('FirstName')
    # LastNameReq = request.json.get('LastName')
    # PhoneNumberReq = request.json.get('PhoneNumber')
    # BirthdayReq = request.json.get('Birthday')
    # HeightReq = request.json.get('Height')
    # PhotoReq = request.json.get('Photo')
    # IdGenderCategoryReq = request.json.get('IdGenderCategory')
    # IdSidePreferenceCategoryReq = request.json.get('IdSidePreferenceCategory')
    # IdCityReq = request.json.get('IdCity')
    # IdSportReq = request.json.get('IdSport')

    # usuario = db.session.query(User)\
    #         .filter(User.IdUser==IdUserReq)\
    #         .first()

    # usuario.FirstName = FirstNameReq
    # usuario.LastName = LastNameReq
    # usuario.PhoneNumber = PhoneNumberReq
    # usuario.Birthday = BirthdayReq
    # usuario.Height = HeightReq
    # usuario.Photo = PhotoReq
    # usuario.IdGenderCategory = IdGenderCategoryReq
    # usuario.IdSidePreferenceCategory = IdSidePreferenceCategoryReq
    # usuario.IdCity = IdCityReq
    # usuario.IdSport = IdSportReq

    # db.session.commit()

    # return "Usuario alterado", 201

    # #Todas as cidades
    # resultado = db.session.query(City)\
    #         .join(State,City.IdState==State.IdState)\
    #         .filter(State.UF.in_(UFReq))\
    #         .all()

    #retorno = []

    # for stateReq in UFReq:
    #     menorIdCity = 99999
    #     for resultadoCity in resultado:
    #         if (resultadoCity.IdCity < menorIdCity) and (resultadoCity.State.UF == stateReq):
    #             menorCidade = resultadoCity.City
    #             menorIdCity = resultadoCity.IdCity
    #     cidadeFiltrada.append(menorCidade)

    # #Caso não achar cidade
    # if len(cidadeFiltrada) == 0:
    #     return "Cidade não encontrada", 201

    # for usuario in usuarios:
    #     retorno.append(usuario.RankCategory.RankName)

    #return jsonify(Nivel = retorno), 201


    ### ADICIONAR USUÁRIO

    # FirstNameReq = request.json.get('FirstName')
    # LastNameReq = request.json.get('LastName')
    # PhoneNumberReq = request.json.get('PhoneNumber')
    # BirthdayReq = request.json.get('Birthday')
    # HeightReq = request.json.get('Height')
    # PhotoReq = request.json.get('Photo')
    # IdGenderCategoryReq = request.json.get('IdGenderCategory')
    # IdSidePreferenceCategoryReq = request.json.get('IdSidePreferenceCategory')
    # IdCityReq = request.json.get('IdCity')
    # IdSportReq = request.json.get('IdSport')

    # usuarioNovo = User(
    #     IdUser = 1,
    #     FirstName = FirstNameReq,
    #     LastName = LastNameReq,
    #     PhoneNumber = PhoneNumberReq,
    #     Birthday = BirthdayReq,
    #     Height = HeightReq,
    #     Photo = PhotoReq,
    #     IdGenderCategory = IdGenderCategoryReq,
    #     IdSidePreferenceCategory = IdSidePreferenceCategoryReq,
    #     IdCity = IdCityReq,
    #     IdSport = IdSportReq,
    # )

    # db.session.add(usuarioNovo)
    # db.session.commit()

    # return "Usuario adicionado", 201