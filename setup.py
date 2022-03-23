import time
import wget
import ssl
import os
from sh import gunzip

# Ignore ssl
ssl._create_default_https_context = ssl._create_unverified_context
# Define the local filename to save data
local_file = 'title.basics.tsv.gz'

print("##########-Clean Up-##########")
cmd = "docker-compose down -v"
print(cmd)
os.system(cmd)
os.system("rm -rf postgres/" + local_file)
os.system("rm -rf postgres/title.basics.tsv")

# Define the remote file to retrieve
remote_url = 'https://datasets.imdbws.com/title.basics.tsv.gz'

# Make http request for remote file data
print("Downloading dataset '" + local_file + "' from " + remote_url)
wget.download(remote_url,"postgres/"  + local_file)

# Extract Archive
print("\n##########-Extracting Archive.-##########")
try:
    gunzip("postgres/" + local_file)
except Exception as err:
    print("{}".format(err))

# run containers
print("##########-Starting Containers...-##########")
cmd = "docker-compose up -d --build"
print(cmd)
os.system(cmd)

print("##########-Clean Up-##########")
os.system("rm -rf postgres/" + local_file)
os.system("rm -rf postgres/title.basics.tsv")
os.system("rm -rf postgres/*.tmp")
print("##########-Test API-##########")
time.sleep(18)
cmd = "curl localhost:3000/api/v1/movies | python3 -m json.tool"
print(cmd)
os.system(cmd)