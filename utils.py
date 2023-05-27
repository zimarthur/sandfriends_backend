from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

def getLastDayOfMonth():
    next_month = datetime.today().replace(day=28) + timedelta(days=4)
    res = next_month - timedelta(days=next_month.day)
    return res.date()

def firstSundayOnNextMonth():
    lastDayOfMonth = getLastDayOfMonth()
    return lastDayOfMonth + timedelta(days=(6 - lastDayOfMonth.weekday()))