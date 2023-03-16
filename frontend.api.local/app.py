from flask import Flask
import requests,jsonify
import urllib
import os

url = os.environ.get("INDEX_URL")
app = Flask(__name__)

@app.route("/")
def home():
    resp = requests.get(url)

    return f"<h1>Welcome to Api Frontend</h1><br \>Getting records from api index {url}: --> <br \> %s " %  (resp.content)

@app.route("/health")
def health():
    return "<h1>100% Healthy</h1>" 

@app.route("/frontend")
def frontend():
    return "<h1>Frontend</h1>" 

@app.errorhandler(500)
def internal_server_error(e):
    # note that we set the 500 status explicitly
    return f"<h2>Api Frontend Error 500</h2><br \><h3>Unable to get to api endpoint(s)</h3> \
            Endpoint(s) --> {url}", 500