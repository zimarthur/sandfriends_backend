from flask import Blueprint, jsonify, abort, request
from datetime import datetime, timedelta, date
from ..extensions import db

from ..Models.match_model import Match
from ..Models.match_member_model import MatchMember
from ..Models.reward_month_model import RewardMonth
from ..Models.reward_category_model import RewardCategory
from ..Models.reward_month_item_model import RewardMonthItem
from ..Models.reward_item_model import RewardItem
from ..Models.reward_user_model import RewardUser

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

    if matches > reward.NTimesToReward:
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

@bp_reward.route('/RewardUserStatus/<idUser>', methods=['GET'])
def RewardUserStatus(idUser):
    #check if user completed month reward
    rewardsUser = db.session.query(RewardUser)\
                .filter(RewardUser.IdUser == idUser)\
                .all()
    rewardsUserList = []
    for rewardUser in rewardsUser:
        rewardsUserList.append(rewardUser.to_json())

    return {'RewardUser': rewardsUserList}