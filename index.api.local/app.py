from flask import Flask
import requests,jsonify
import urllib
url = 'http://nodeapi.api.local:3000/api/v1/movies/'
app = Flask(__name__)

@app.route("/")
def home():
    # Making a get request
    resp = requests.get(url)
    return f"<h2>Welcome to Nodeapi Index Version 1</h2><br \><h3>Movies</h3>Getting movie records from api {url}: --> <br \> %s " %  (resp.content)
#    return "<h1>Welcome to Api Home Page</h1>Getting movie records from api " + url + "-> %s Getting tvSeries records from api " + url + "-> %s " %  (resp.json(), resp2.json())


@app.route("/health")
def health():
    return "<h1>100% Healthy</h1>" 

@app.route("/index")
def index():
    return "<h1>Index Version 1</h1>" 

@app.errorhandler(500)
def internal_server_error(e):
    # note that we set the 500 status explicitly
    return f"<h2>Nodeapi Index Version 1 Error code 500</h2><br \><h3>Unable to get to api endpoints</h3> \
            Endpoint(s) --> {url} ", 500