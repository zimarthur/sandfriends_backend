import requests
import json

with open('/sandfriends/sandfriends_backend/URL_config.json') as config_file:
    URL_list = json.load(config_file)

asaas_url = URL_list.get('URL_ASAAS')
asaas_api_key = URL_list.get('ASAAS_API_KEY')

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "access_token": asaas_api_key
}

def requestPost(endPoint, payload):
    return requests.post(asaas_url + endPoint, headers=headers, json= payload)