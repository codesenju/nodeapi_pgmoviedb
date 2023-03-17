from flask import Flask
import requests,jsonify
import urllib

import os

url_movies = os.environ.get("MOVIES_URL")

app = Flask(__name__)

@app.route("/")
def home():
    # Making a get request
    resp = requests.get(url)
    return f"<h2>Welcome to Nodeapi Index Version 1</h2><br \><h3>Movies</h3>Getting movie records from api {url_movies}: --> <br \> %s " %  (resp.content)

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
            Endpoint(s) --> {url_movies} ", 500