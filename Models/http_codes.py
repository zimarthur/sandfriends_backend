class HttpCode:
    SUCCESS = 200
    ABORT = 400
    #Warning gera uma carinha triste no site
    WARNING = 230
    #Alert gera uma carinha feliz no site
    ALERT = 231
    #Resposta para quando o access token enviado na solicitação não é válido
    EXPIRED_TOKEN = 232

    #Antigos
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
    CITY_NOT_FOUND = 417
    STATE_NOT_FOUND = 418
    CITY_STATE_NOT_MATCH = 419
    CNPJ_ALREADY_USED = 420
    WAITING_APPROVAL = 421
    STORE_ALREADY_APPROVED = 423
    NAME_ALREADY_USED = 424
    ADDRESS_ALREADY_USED = 425
    INFORMATION_NOT_FOUND = 426

###RETURNS
# 0- Success
# 1- Invalid Token
# 2- Invalid Email
# 3- Invalid Password
##########