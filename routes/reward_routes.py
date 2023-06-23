from flask import Blueprint, jsonify, abort, request
from datetime import datetime, timedelta, date
from ..extensions import db
from sqlalchemy import func

from ..Models.match_model import Match
from ..Models.user_model import User
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
            newRewardUser = RewardUser(
                RewardClaimed = False,
                IdUser =  idUser,
                IdRewardMonth = reward.IdRewardMonth,
                IdRewardItem = None,
                RewardClaimedDate = None,
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
    
    rewardCodeReq = request.json.get('RewardCode')

    reward = db.session.query(RewardUser).filter(RewardUser.IdRewardUser == rewardCodeReq).first()

    if reward is None:
        return webResponse("Código não encontrado", "Confirme que o código inserido é o mesmo do aplicativo do jogador"), HttpCode.WARNING

    if reward.RewardClaimed:
        return webResponse("Recompensa já foi retirada", None), HttpCode.WARNING

    rewardsItemsList = []
    for rewardItemMonth in reward.RewardMonth.Rewards:
        rewardsItemsList.append(rewardItemMonth.RewardItem.to_json())

    return {'RewardItems': rewardsItemsList}, HttpCode.SUCCESS