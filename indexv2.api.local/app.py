from flask import Flask
import requests,jsonify
import urllib
import os
url_movies = os.environ.get("MOVIES_URL")
url_tvseries = os.environ.get("TVSERIES_URL")
url_tvminiseries = os.environ.get("TVMINISERIES_URL")
app = Flask(__name__)

@app.route("/")
def home():
    # Making a get request
    resp = requests.get(url_movies)
    resp2 = requests.get(url_tvseries)
    resp3 = requests.get(url_tvminiseries)
    return f"<h2>Welcome to Nodeapi Index Version 2</h2><br \><h3>Movies</h3>Getting movie records from api {url_movies}: --> <br \> %s \
    <br \><h3>TV Series</h3>Getting tvSeries records from api {url_tvseries}: --> <br \> %s \
    <br \><h3>TV Mini Series</h3>Getting tvMiniSeries records from api {url_tvminiseries}: --> <br \> %s" %  (resp.content, resp2.content, resp3.content)

@app.route("/healthz")
def health():
    return "<h1>100% Healthy</h1>" 

@app.route("/index")
def index():
    return "<h1>Index Version 2</h1>" 

@app.errorhandler(500)
def internal_server_error(e):
    # note that we set the 500 status explicitly
    return f"<h2>Nodeapi Index Version 2 Error code 500</h2><br \><h3>Unable to get to api endpoints</h3> \
            Endpoint(s) --> {url_movies}, {url_tvseries}, {url_tvminiseries} ", 500