from flask import Flask
import requests,jsonify
import urllib

url_tvminiseriesfifa = 'http://nodeapi:3000/api/v1/tvminiseries/2022 Fifa World Cup'
url_endgame = 'http://nodeapi:3000/api/v1/movies/Avengers: Endgame'
app = Flask(__name__)

@app.route("/")
def home():
    # url = 'http://nodeapi.service.local:3000/api/v1/movies/'
    # url = 'http://localhost:3000/api/v1/movies/'
    # Making a get request
#    resp = requests.get(url)
#    resp2 = requests.get(url_tvseries)
#    resp3 = requests.get(url_tvminiseries)
    resp4 = requests.get(url_tvminiseriesfifa)
    resp5 = requests.get(url_endgame)
    return f"<h4>Welcome to Index Backend</h4> \
    <h5>World Cup</h5>Getting World Cup records from api {url_tvminiseriesfifa}: --> <br \> %s \
    <h5>Avengers Endgame</h5>Getting Avengers Endgame records from api {url_endgame}: --> <br \> %s " %  (resp4.content, resp5.content)
#    return "<h1>Welcome to Api Home Page</h1>Getting movie records from api " + url + "-> %s Getting tvSeries records from api " + url + "-> %s " %  (resp.json(), resp2.json())

@app.route("/health")
def health():
    return "<h1>100% Healthy</h1>" 

@app.route("/index-backend")
def index():
    return "<h1>Index-Backend</h1>" 


@app.errorhandler(500)
def internal_server_error(e):
    # note that we set the 500 status explicitly
    return "<h2>Index Backend Error code 500</h2><br \><h3>Unable to get to api endpoints</h3> \
            Endpoint(s) --> {url_tvminiseriesfifa}, {url_endgame}  ", 500