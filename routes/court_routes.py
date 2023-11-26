from flask import Blueprint, jsonify, abort, request
from datetime import datetime, timedelta, date
from ..Models.store_model import Store
from ..utils import firstSundayOnNextMonth, lastSundayOnLastMonth
from ..extensions import db
from ..responses import webResponse
from ..Models.http_codes import HttpCode
from ..Models.city_model import City
from ..Models.state_model import State
from ..Models.sport_model import Sport
from ..Models.match_model import Match
from ..Models.employee_model import Employee
from ..Models.available_hour_model import AvailableHour
from ..Models.store_court_model import StoreCourt
from ..Models.store_price_model import StorePrice
from ..Models.store_court_sport_model import StoreCourtSport
from sqlalchemy import func
import base64

bp_court = Blueprint('bp_court', __name__)

@bp_court.route('/AddCourt', methods=['POST'])
def AddCourt():
    if not request.json:
        abort(400)

    accessTokenReq = request.json.get('AccessToken')

    #busca a loja a partir do token do employee
    store = db.session.query(Store).\
            join(Employee, Employee.IdStore == Store.IdStore).\
            filter(Employee.AccessToken == accessTokenReq).first()
    
    #Caso não encontrar Token
    if store is None:
        return webResponse("Token não encontrado", None), HttpCode.EXPIRED_TOKEN

    descriptionReq = request.json.get('Description')
    isIndoorReq = request.json.get('IsIndoor')

    newCourt = StoreCourt(
        IdStore = store.IdStore,
        Description = descriptionReq.title(),
        IsIndoor = isIndoorReq,
    )

    db.session.add(newCourt)
    db.session.commit()
    db.session.refresh(newCourt)

    sportsReq = request.json.get('Sports')

    for sport in sportsReq:
        newSport = StoreCourtSport(
            IdStoreCourt = newCourt.IdStoreCourt,
            IdSport = sport["IdSport"]
        )
        db.session.add(newSport)

    operationDaysReq = request.json.get('OperationDays')

    for operationDay in operationDaysReq:
        weekday = operationDay["Weekday"]
        for price in operationDay["Prices"]:
            newStorePrice = StorePrice(
                IdStoreCourt = newCourt.IdStoreCourt,
                Weekday = weekday,
                IdAvailableHour = price["IdHour"],
                Price = price["Price"],
                RecurrentPrice = price["RecurrentPrice"],
            )
            db.session.add(newStorePrice)

    db.session.commit()

    #Lista com as quadras do estabelecimento(json da quadra, esportes e preço)
    courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == store.IdStore).all()
    courtsList = []

    for court in courts:
        courtsList.append(court.to_json_full())

    return jsonify({'Courts':courtsList}), HttpCode.SUCCESS


@bp_court.route('/RemoveCourt', methods=['POST'])
def RemoveCourt():
    if not request.json:
        abort(400)

    accessTokenReq = request.json.get('AccessToken')
    idStoreCourtReq = request.json.get('IdStoreCourt')

    #busca a loja a partir do token do employee
    court = db.session.query(StoreCourt).\
            join(Employee, Employee.IdStore == StoreCourt.IdStore)\
            .filter(Employee.AccessToken == accessTokenReq)\
            .filter(StoreCourt.IdStoreCourt == idStoreCourtReq).first()
    

    #Caso não encontrar Token
    if court is None:
        return webResponse("Token não encontrado", None), HttpCode.EXPIRED_TOKEN

    matches = db.session.query(Match)\
        .filter((Match.Date > datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.IdTimeBegin >= int(datetime.now().strftime("%H")))))\
        .filter(Match.IdStoreCourt == court.IdStoreCourt)\
        .filter(Match.Canceled == False).count()

    if(matches > 0):
        if( matches == 1):
            return webResponse("Não foi possível remover a quadra", "Existe 1 partida agendada que ainda não ocorreu."), HttpCode.WARNING
        else:
            return webResponse("Não foi possível remover a quadra", "Existem {} partidas agendadas que ainda não ocorreram.".format(matches)), HttpCode.WARNING
            
    #remove os esportes da quadra
    courtSports = db.session.query(StoreCourtSport).filter(StoreCourtSport.IdStoreCourt == court.IdStoreCourt).all()
    for courtSport in courtSports:
        db.session.delete(courtSport)

    #remove os preços da quadra
    courtPrices = db.session.query(StorePrice).filter(StorePrice.IdStoreCourt == court.IdStoreCourt).all()
    for courtPrice in courtPrices:
        db.session.delete(courtPrice)

    #remove a quadra
    db.session.delete(court)

    db.session.commit()

    #Lista com as quadras do estabelecimento(json da quadra, esportes e preço)
    courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == court.IdStore).all()
    courtsList = []

    for court in courts:
        courtsList.append(court.to_json_full())

    return jsonify({'Courts':courtsList}), HttpCode.SUCCESS

@bp_court.route('/SaveCourtChanges', methods=['POST'])
def SaveCourtChanges():
    if not request.json:
        abort(400)

    accessTokenReq = request.json.get('AccessToken')
    courtsReq = request.json.get('Courts')

    #busca a loja a partir do token do employee
    accessTokenValid = db.session.query(StoreCourt).\
            join(Employee, Employee.IdStore == StoreCourt.IdStore)\
            .filter(Employee.AccessToken == accessTokenReq)\
            .filter(StoreCourt.IdStoreCourt == courtsReq[0]["IdStoreCourt"]).first()
    

    #Caso não encontrar Token
    if accessTokenValid is None:
        return webResponse("Token não encontrado", None), HttpCode.EXPIRED_TOKEN

    for courtReq in courtsReq:
        court = db.session.query(StoreCourt).filter(StoreCourt.IdStoreCourt == courtReq["IdStoreCourt"]).first()
        court.Description = courtReq["Description"]
        court.IsIndoor = courtReq["IsIndoor"]
        
        #busca as partidas futuras e não canceladas nessa quadra a ser editada
        matches = db.session.query(Match)\
            .filter((Match.Date > datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.IdTimeBegin >= int(datetime.now().strftime("%H")))))\
            .filter(Match.IdStoreCourt == court.IdStoreCourt)\
            .filter(Match.Canceled == False).all()
        
        #coloca nessa lista todos os esportes disponiveis vindos da requisição
        sportsReq = []
        for sportReq in courtReq["Sports"]:
            sportsReq.append(sportReq["IdSport"])
        
        #loop pelos esportes da quadra que já estão no banco de dados
        courtSports = db.session.query(StoreCourtSport).filter(StoreCourtSport.IdStoreCourt == court.IdStoreCourt).all()
        for courtSport in courtSports:
            #se o q veio da requisição já ta no banco de dados, não precisa fazer nada
            if courtSport.IdSport in sportsReq:
                sportsReq.remove(courtSport.IdSport)
            else:
                #esporte que tava no banco de dados não veio na requisição, portanto tem q excluir. Antes verifica se tem alguma partida com esse esporte que querem remover
                #se tema alguma partida já, cancela requisição
                if len([match for match in matches if match.IdSport == courtSport.IdSport]) > 0:
                    return webResponse("Não completar completar suas alterações", "Existe uma futura partida de um esporte que você quis remover."), HttpCode.WARNING
                db.session.delete(courtSport)

        #add no db os novos esportes
        for newIdSport in sportsReq:
            newSport = StoreCourtSport(
                IdStoreCourt = court.IdStoreCourt,
                IdSport = newIdSport,
            )
            db.session.add(newSport)


        

        #loop pelos preços da quadra que já estão no banco de dados
        courtPrices = db.session.query(StorePrice).filter(StorePrice.IdStoreCourt == court.IdStoreCourt).all()
        #esse primeiro loop é pra add novos horários e alterar os ja existentes
        for operationDayReq in courtReq["OperationDays"]:
            for priceReq in operationDayReq["Prices"]:
                courtPrice = [courtPriceFiltered for courtPriceFiltered in courtPrices if courtPriceFiltered.Weekday == operationDayReq["Weekday"] and courtPriceFiltered.IdAvailableHour == priceReq["IdHour"]]
                #return webResponse(len(courtPrice), "Existe uma futura partida de um esporte que você quis remover."), HttpCode.WARNING
                if len(courtPrice) == 0:
                    newCourtPrice = StorePrice(
                        Weekday = operationDayReq["Weekday"],
                        Price = priceReq["Price"],
                        RecurrentPrice = priceReq["RecurrentPrice"],
                        IdAvailableHour = priceReq["IdHour"],
                        IdStoreCourt = court.IdStoreCourt,
                    )
                    db.session.add(newCourtPrice)
                else:
                    courtPrice[0].Price = priceReq["Price"]
                    courtPrice[0].RecurrentPrice = priceReq["RecurrentPrice"]
        
        #esse é pra apagar os que não apareceram na requisição
        for courtPrice in courtPrices:
            concurrentMatches = [match for match in matches if match.IdTimeBegin == courtPrice.IdAvailableHour]
            equivalentOperationDay = [operationDay for operationDay in courtReq["OperationDays"] if operationDay["Weekday"] == courtPrice.Weekday]
            if len(equivalentOperationDay) == 0:
                if len(concurrentMatches) > 0:
                    return webResponse("Não completar completar suas alterações", "Existe uma futura partida em um horário que você quis remover."), HttpCode.WARNING
                db.session.delete(courtPrice)
            else:
                equivalentCourtPrice = [courtPriceFiltered for courtPriceFiltered in equivalentOperationDay[0]["Prices"] if courtPrice.IdAvailableHour == courtPriceFiltered["IdHour"]]
                if len(equivalentCourtPrice) == 0:
                    if len(concurrentMatches) > 0:
                        return webResponse("Não completar completar suas alterações", "Existe uma futura partida em um horário que você quis remover."), HttpCode.WARNING
                    db.session.delete(courtPrice)
    
    db.session.commit()

    #Lista com as quadras do estabelecimento(json da quadra, esportes e preço)
    courts = db.session.query(StoreCourt).filter(StoreCourt.IdStore == court.IdStore).all()
    courtsList = []

    for court in courts:
        courtsList.append(court.to_json_full())

    return jsonify({'Courts':courtsList}), HttpCode.SUCCESS

#Verifica se um cupom de desconto é válido e usa ele
#Precisa dos dados da store e match pra verificar se o cupom se aplica
#def useCoupon(code, store, match):
