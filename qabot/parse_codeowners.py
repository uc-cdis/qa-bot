import requests

GITHUBLINK = "https://raw.githubusercontent.com/uc-cdis/cdis-manifest/master/CODEOWNERS"
CODEOWNERS = requests.get(GITHUBLINK).text

envdict = {}
lines = CODEOWNERS.splitlines()

for line in lines:
    if line != "":
        (envJson, githubID, planxqa) = line.split()
        env = envJson.split("/")[0]
        envdict[env] = githubID

# print(envdict)
