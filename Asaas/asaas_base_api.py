import requests
import os

asaas_url = os.environ['URL_ASAAS']
asaas_api_key = os.environ['ASAAS_API_KEY']

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "access_token": asaas_api_key
}

def requestPost(endPoint, payload):
    return requests.post(asaas_url + endPoint, headers=headers, json= payload)