from flask import Blueprint, jsonify, abort, request
from datetime import datetime, timedelta, date
from ..extensions import db
from sqlalchemy import func
import random
import string

from ..Models.match_model import Match
from ..Models.user_model import User
from ..Models.store_model import Store
from ..Models.employee_model import Employee
from ..Models.match_member_model import MatchMember
from ..Models.reward_month_model import RewardMonth
from ..Models.reward_category_model import RewardCategory
from ..Models.reward_month_item_model import RewardMonthItem
from ..Models.reward_item_model import RewardItem
from ..Models.reward_user_model import RewardUser
from ..Models.http_codes import HttpCode
from ..responses import webResponse
bp_reward = Blueprint('bp_reward', __name__)

def generateRewardCode():
    characters = string.ascii_uppercase + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(6))
    return random_string

@bp_reward.route('/RewardStatus/<idUser>', methods=['GET'])
def RewardStatus(idUser):

    reward = db.session.query(RewardMonth)\
                .filter((RewardMonth.StartingDate <= datetime.today().date()) & (RewardMonth.EndingDate >= datetime.today().date()))\
                .first()

    matches = db.session.query(Match)\
                .join(MatchMember, MatchMember.IdMatch == Match.IdMatch)\
                .filter((MatchMember.IdUser == idUser) & (MatchMember.IsMatchCreator == True))\
                .filter((Match.Date >= reward.StartingDate) & (Match.Date <= reward.EndingDate))\
                .filter((Match.Date < datetime.today().date()) | ((Match.Date == datetime.today().date()) & (Match.IdTimeBegin <= int(datetime.now().strftime("%H")))))\
                .filter(Match.Canceled == False)\
                .count()

    if matches >= reward.NTimesToReward:
        matches = reward.NTimesToReward
        #check if reward is in reward_user
        rewardUser = db.session.query(RewardUser)\
                    .filter(RewardUser.IdUser == idUser)\
                    .filter(RewardUser.IdRewardMonth == reward.IdRewardMonth).first()
        if rewardUser is None:
            isNewRewardCodeUnique = False
            while isNewRewardCodeUnique == False:
                newRewardCode = generateRewardCode()
                rewardCodeCheck = db.session.query(RewardUser)\
                        .filter(RewardUser.RewardClaimCode == newRewardCode).first()
                if rewardCodeCheck is None:
                    isNewRewardCodeUnique = True

            newRewardUser = RewardUser(
                RewardClaimed = False,
                IdUser =  idUser,
                IdRewardMonth = reward.IdRewardMonth,
                IdRewardItem = None,
                RewardClaimedDate = None,
                RewardClaimCode = newRewardCode,
            )
            db.session.add(newRewardUser)
            db.session.commit()


    return {'Reward': reward.to_json(), 'UserRewardQuantity':matches}

@bp_reward.route('/UserRewardsHistory', methods=['POST'])
def UserRewardsHistory():

    accessTokenReq = request.json.get('AccessToken')

    user = db.session.query(User).filter(User.AccessToken == accessTokenReq).first()

    if user is None:
        return '1', HttpCode.EXPIRED_TOKEN

    userRewards = db.session.query(RewardUser)\
                .filter(RewardUser.IdUser == user.IdUser)\
                .all()

    userRewardsList = []
    for userReward in userRewards:
        userRewardsList.append(userReward.to_json())

    return {'UserRewards': userRewardsList}, HttpCode.SUCCESS

@bp_reward.route('/SearchCustomRewards', methods=['POST'])
def SearchCustomRewards():

    accessTokenReq = request.json.get('AccessToken')
    dateStartReq = datetime.strptime(request.json.get('DateStart'), '%d/%m/%Y')
    dateEndReq = datetime.strptime(request.json.get('DateEnd'), '%d/%m/%Y')

    employee = db.session.query(Employee).filter(Employee.AccessToken == accessTokenReq).first()

    if employee is None:
        return '1', HttpCode.EXPIRED_TOKEN

    rewards = db.session.query(RewardUser)\
                    .filter(RewardUser.IdStore == employee.IdStore)\
                    .filter((func.DATE(RewardUser.RewardClaimedDate) >= dateStartReq.date()) & (func.DATE(RewardUser.RewardClaimedDate) <= dateEndReq.date())).all()

    rewardsList = []
    for reward in rewards:
        rewardsList.append(reward.to_json_store())

    return {'Rewards': rewardsList}, HttpCode.SUCCESS


@bp_reward.route('/SendUserRewardCode', methods=['POST'])
def SendUserRewardCode():
    
    rewardCodeReq = request.json.get('RewardClaimCode')

    reward = db.session.query(RewardUser).filter(RewardUser.RewardClaimCode == rewardCodeReq).first()

    if reward is None:
        return webResponse("Código não encontrado", "Confirme que o código inserido é o mesmo do aplicativo do jogador"), HttpCode.WARNING

    if reward.RewardClaimed:
        return webResponse("Recompensa já foi retirada", None), HttpCode.WARNING

    rewardsItemsList = []
    for rewardItemMonth in reward.RewardMonth.Rewards:
        rewardsItemsList.append(rewardItemMonth.RewardItem.to_json())

    return {'RewardItems': rewardsItemsList}, HttpCode.SUCCESS


@bp_reward.route('/UserRewardSelected', methods=['POST'])
def UserRewardSelected():
    
    accessTokenReq = request.json.get('AccessToken')
    rewardCodeReq = request.json.get('RewardClaimCode')
    rewardItemReq = request.json.get('RewardItem')

    #busca a loja a partir do token do employee
    store = db.session.query(Store).\
            join(Employee, Employee.IdStore == Store.IdStore).\
            filter(Employee.AccessToken == accessTokenReq).first()
    
    #Caso não encontrar Token
    if store is None:
        return webResponse("Token não encontrado", None), HttpCode.WARNING

    reward = db.session.query(RewardUser).filter(RewardUser.RewardClaimCode == rewardCodeReq).first()

    if reward is None or reward.RewardClaimed:
        return webResponse("Recompensa já foi retirada", None), HttpCode.WARNING
    
    reward.IdRewardItem = rewardItemReq
    reward.RewardClaimed = True
    reward.RewardClaimedDate = datetime.now()
    reward.IdStore = store.IdStore

    db.session.commit()

    return webResponse("Recompensa registrada", "Entregue um/a "+reward.RewardItem.Description + " para "+reward.User.FirstName+"." ), HttpCode.ALERT