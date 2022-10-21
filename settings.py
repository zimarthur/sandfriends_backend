from mailjet_rest import Client

api_key = '8ca92dfd5c3d9c6234348a5a8b06b249'
api_secret = 'a694ad20fe5c568939a31f74e37efc61'
mailjet = Client(auth=(api_key, api_secret), version='v3.1')