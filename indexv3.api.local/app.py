from flask import Flask
import requests,jsonify
import urllib
url = 'http://nodeapi.api.local:3000/api/v1/movies/'
url_tvseries = 'http://nodeapi.api.local:3000/api/v1/tvseries/'
url_tvminiseries = 'http://nodeapi.api.local:3000/api/v1/tvminiseries/'
# url_tvminiseriesfifa = 'http://nodeapi.api.local:3000/api/v1/tvminiseries/2022 Fifa World Cup'
# url_endgame = 'http://nodeapi.api.local:3000/api/v1/movies/Avengers: Endgame'
url_backend = 'http://index-backend.api.local:5000'
app = Flask(__name__)

@app.route("/")
def home():
    # url = 'http://nodeapi.service.local:3000/api/v1/movies/'
    # url = 'http://localhost:3000/api/v1/movies/'
    # Making a get request
    resp = requests.get(url)
    resp2 = requests.get(url_tvseries)
    resp3 = requests.get(url_tvminiseries)
    resp4 = requests.get(url_backend)
    return f"<h2>Welcome to Nodeapi Index Version 3</h2><br \><h3>Movies</h3>Getting movie records from api {url}: --> <br \> %s \
    <br \><h3>TV Series</h3>Getting tvSeries records from api {url_tvseries}: --> <br \> %s \
    <br \><h3>TV Mini Series</h3>Getting tvMiniSeries records from api {url_tvminiseries}: --> <br \> %s \
    <br \><h3>World Cup & Avengers Endgame</h3>Getting records from api {url_backend}: --> <br \> %s  " %  (resp.content, resp2.content, resp3.content, resp4.content)
#    return "<h1>Welcome to Api Home Page</h1>Getting movie records from api " + url + "-> %s Getting tvSeries records from api " + url + "-> %s " %  (resp.json(), resp2.json())
    
@app.errorhandler(500)
def internal_server_error(e):
    # note that we set the 500 status explicitly
    return f"<h2>Nodeapi Index Version 3 Error code 500</h2><br \><h3>Unable to get to api endpoints</h3> \
            Endpoint(s) --> {url}, {url_tvseries}, {url_tvminiseries}, {url_backend} ", 500