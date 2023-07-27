from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

def getFirstDayOfLastMonth():
    return (datetime.today().replace(day=1) - timedelta(days=1)).replace(day=1).date()

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

def isCurrentMonth(date):
    return date.month == datetime.today().month and date.year == datetime.today().year

weekdays =[
    "Segundas-feiras",
    "Terças-feiras",
    "Quartas-feiras",
    "Quintas-feiras",
    "Sextas-feiras",
    "Sábados",
    "Domingos"
]