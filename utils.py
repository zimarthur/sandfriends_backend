from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

def getLastDayOfMonth(date):
    next_month = date.replace(day=28) + timedelta(days=4)
    res = next_month - timedelta(days=next_month.day)
    return res.date()

def firstSundayOnNextMonth(date):
    lastDayOfMonth = getLastDayOfMonth(date)
    return lastDayOfMonth + timedelta(days=(6 - lastDayOfMonth.weekday()))

def lastSundayOnLastMonth(date):
    firstDayOfMonth = date.replace(day = 1)
    return firstDayOfMonth - timedelta(days=(firstDayOfMonth.weekday()))