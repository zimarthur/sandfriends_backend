class HttpCode:
    SUCCESS = 200
    ABORT = 400
    INVALID_ACCESS_TOKEN = 401
    INVALID_USER_ID = 402  #user id não encontrado
    EMAIL_ALREADY_USED = 403 #tentou criar uma conta com um email ja cadastrado e a senha não condiz com o email
    EMAIL_ALREADY_USED_THIRDPARTY = 404 #o email já foi usado pra criar conta com o google
    WAITING_EMAIL_CONFIRMATION = 405
    INVALID_EMAIL_CONFIRMATION_TOKEN = 406
    EMAIL_NOT_FOUND = 407
    INVALID_PASSWORD = 408
    ACCOUNT_ALREADY_CREATED = 409 #tentou criar uma conta que já estava valida
    INVALID_RESET_PASSWORD_VALUE = 410
    EMAIL_ALREADY_CONFIRMED = 411
    NO_SEARCH_RESULTS = 412
    TIME_NO_LONGER_AVAILABLE = 413
    MATCH_NOT_FOUND = 414
    MATCH_ALREADY_FINISHED = 415
    MATCH_CANCELLED = 416
    CANCELLATION_PERIOD_EXPIRED = 416

###RETURNS
# 0- Success
# 1- Invalid Token
# 2- Invalid Email
# 3- Invalid Password
##########