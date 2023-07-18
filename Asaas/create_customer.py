from ..Asaas.asaas_base_api import requestPost

def createCustomer(user):
    response = requestPost(
        "customers", 
        {
            "name": f"{user.FirstName} {user.LastName}",
            "email": user.Email,
            "phone": user.PhoneNumber,
            "externalReference": user.IdUser,
            "notificationDisabled": False,
            }
        )
    return response


   