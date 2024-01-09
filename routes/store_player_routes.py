from flask import Blueprint, jsonify, abort, request
from ..Models.sport_model import Sport
from ..Models.store_model import Store
from ..Models.store_player_model import StorePlayer
from ..Models.match_model import Match
from ..Models.match_member_model import MatchMember
from ..Models.employee_model import Employee, getEmployeeByToken
from ..Models.http_codes import HttpCode
from ..responses import webResponse

from ..extensions import db

bp_store_player = Blueprint('bp_store_player', __name__)

@bp_store_player.route('/AddStorePlayer', methods=['POST'])
def AddStorePlayer():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessTokenReq = request.json.get('AccessToken')

    firstNameReq = request.json.get('FirstName').title()
    lastNameReq = request.json.get('LastName').title()
    phoneNumberReq = request.json.get('PhoneNumber')
    idGenderCategoryReq = request.json.get('IdGenderCategory')
    idSportReq = request.json.get('IdSport')
    idRankCategoryReq = request.json.get('IdRankCategory')

    employee = getEmployeeByToken(accessTokenReq)

    #Caso não encontrar Token
    if employee is None:
        return webResponse("Token não encontrado", None), HttpCode.EXPIRED_TOKEN

    newStorePlayer = StorePlayer(
        IdStore = employee.IdStore,
        FirstName = firstNameReq,
        LastName = lastNameReq,
        PhoneNumber = phoneNumberReq,
        IdGenderCategory = idGenderCategoryReq,
        IdSport = idSportReq,
        IdRankCategory = idRankCategoryReq,
        Deleted = False,
    )

    db.session.add(newStorePlayer)
    db.session.commit()

    (storePlayersList, matchMembersList) = getStorePlayers(employee.Store)

    return jsonify({
        'StorePlayers': storePlayersList,\
        'MatchMembers': matchMembersList\
    }), HttpCode.SUCCESS

@bp_store_player.route('/EditStorePlayer', methods=['POST'])
def EditStorePlayer():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessTokenReq = request.json.get('AccessToken')

    idStorePlayerReq = request.json.get('IdStorePlayer')
    firstNameReq = request.json.get('FirstName').title()
    lastNameReq = request.json.get('LastName').title()
    phoneNumberReq = request.json.get('PhoneNumber')
    idGenderCategoryReq = request.json.get('IdGenderCategory')
    idSportReq = request.json.get('IdSport')
    idRankCategoryReq = request.json.get('IdRankCategory')

    employee = getEmployeeByToken(accessTokenReq)

    #Caso não encontrar Token
    if employee is None:
        return webResponse("Token não encontrado", None), HttpCode.EXPIRED_TOKEN

    storePlayer = db.session.query(StorePlayer).filter(StorePlayer.IdStorePlayer == idStorePlayerReq).first()
    
    #Caso não encontrar Token
    if storePlayer is None:
        return webResponse("Jogador(a) não encontrado(a)", None), HttpCode.WARNING
        
    storePlayer.FirstName = firstNameReq,
    storePlayer.LastName = lastNameReq,
    storePlayer.PhoneNumber = phoneNumberReq,
    storePlayer.IdGenderCategory = idGenderCategoryReq,
    storePlayer.IdSport = idSportReq,
    storePlayer.IdRankCategory = idRankCategoryReq,

    db.session.commit()

    (storePlayersList, matchMembersList) = getStorePlayers(employee.Store)

    return jsonify({
        'StorePlayers': storePlayersList,\
        'MatchMembers': matchMembersList\
    }), HttpCode.SUCCESS

@bp_store_player.route('/DeleteStorePlayer', methods=['POST'])
def DeleteStorePlayer():
    if not request.json:
        abort(HttpCode.ABORT)
    
    accessTokenReq = request.json.get('AccessToken')

    idStorePlayerReq = request.json.get('IdStorePlayer')

    employee = getEmployeeByToken(accessTokenReq)
    
    #Caso não encontrar Token
    if employee is None:
        return webResponse("Token não encontrado", None), HttpCode.EXPIRED_TOKEN

    storePlayer = db.session.query(StorePlayer).filter(StorePlayer.IdStorePlayer == idStorePlayerReq).first()
    
    #Caso não encontrar Token
    if storePlayer is None:
        return webResponse("Jogador(a) não encontrado(a)", None), HttpCode.WARNING

    storePlayer.Deleted = True

    db.session.commit()

    (storePlayersList, matchMembersList) = getStorePlayers(employee.Store)

    return jsonify({
        'StorePlayers': storePlayersList,\
        'MatchMembers': matchMembersList\
    }), HttpCode.SUCCESS

def getStorePlayers(store):
    storePlayers = db.session.query(StorePlayer)\
                    .filter(StorePlayer.IdStore == store.IdStore)\
                    .filter(StorePlayer.Deleted == False).all()

    storePlayersList = []
    for storePlayer in storePlayers:
        storePlayersList.append(storePlayer.to_json())

    matchMembersList = []
    matchMembers = db.session.query(MatchMember)\
                    .join(Match, MatchMember.IdMatch == Match.IdMatch)\
                    .filter(Match.Canceled == False)\
                    .filter(Match.IdStoreCourt.in_([court.IdStoreCourt for court in store.Courts]))\
                    .filter(MatchMember.Quit == False)\
                    .filter(MatchMember.WaitingApproval == False)\
                    .filter(MatchMember.Refused == False).all()
    
    addedIdUsers = []
    for matchMember in matchMembers:
        if matchMember.IdUser not in addedIdUsers and matchMember.IdUser is not None:
            addedIdUsers.append(matchMember.IdUser)
            matchMembersList.append(matchMember.User.to_json_web())

    return  (storePlayersList,matchMembersList)
