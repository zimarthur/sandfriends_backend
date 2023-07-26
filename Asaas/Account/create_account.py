from ..asaas_base_api import requestPost

def createCustomer(store, companyType):
    if store.CNPJ is None or store.CNPJ == "":
        cpfCnpf = store.CPF
    else:
        cpfCnpf = store.CNPJ
    response = requestPost(
        "accounts", 
        {
            "name": store.Name,
            "email": store.StoreOwner.Email,
            "cpfCnpj": cpfCnpf,
            "mobilePhone": store.PhoneNumber1,
            "address": store.Address,
            "addressNumber": store.AddressNumber,
            "province": store.Neighbourhood,
            "postalCode": store.CEP,
            "companyType": companyType,
            }
        )
    return response


   