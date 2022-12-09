from flask import Flask
import requests,jsonify
import urllib
url = 'http://nodeapi.service.local:3000/api/v1/movies/'
app = Flask(__name__)

@app.route("/")
def home():
    # url = 'http://nodeapi.service.local:3000/api/v1/movies/'
    # url = 'http://localhost:3000/api/v1/movies/'
    # Making a get request
    resp = requests.get(url)
    return "<h1>Welcome to Api Home Page</h1>Getting records from api: %s " %  (resp.json())
    
@app.errorhandler(500)
def internal_server_error(e):
    # note that we set the 500 status explicitly
    return "<h3>Unable to get to api endpoint " + url + "</h3>", 500