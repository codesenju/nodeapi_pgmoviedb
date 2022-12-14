from flask import Flask
import requests,jsonify
import urllib
url = 'http://index.api.local:5000'
app = Flask(__name__)

@app.route("/")
def home():
    # url = 'http://nodeapi.service.local:3000/api/v1/movies/'
    # url = 'http://localhost:3000/api/v1/movies/'
    # Making a get request
    resp = requests.get(url)
#    resp2 = requests.get(url_tvseries)
#    resp3 = requests.get(url_tvminiseries)
#    resp4 = requests.get(url_tvminiseriesfifa)
#    resp5 = requests.get(url_endgame)
    return f"<h1>Welcome to Api Frontend</h1><br \>Getting records from api index {url}: --> <br \> %s " %  (resp.content)
#    return "<h1>Welcome to Api Home Page</h1>Getting movie records from api " + url + "-> %s Getting tvSeries records from api " + url + "-> %s " %  (resp.json(), resp2.json())
    
@app.errorhandler(500)
def internal_server_error(e):
    # note that we set the 500 status explicitly
    return f"<h2>Api Frontend Error 500</h2><br \><h3>Unable to get to api endpoint(s)</h3> \
            Endpoint(s) --> {url}", 500