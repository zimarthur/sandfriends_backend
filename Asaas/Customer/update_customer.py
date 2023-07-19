from ..asaas_base_api import requestPost

def updateCpf(user):
    response = requestPost(
        f"customers/{user.AsaasId}", 
        {
            "cpfCnpj": user.Cpf,
        }
    )
    return response


   