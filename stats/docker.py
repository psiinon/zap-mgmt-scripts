'''
Script for collecting and processing the ZAP docker stats
'''
import utils

urls = {
    "stable": "https://registry.hub.docker.com/v2/repositories/owasp/zap2docker-stable/",
    "weekly": "https://registry.hub.docker.com/v2/repositories/owasp/zap2docker-weekly/",
    "live": "https://registry.hub.docker.com/v2/repositories/owasp/zap2docker-live/",
    "bare": "https://registry.hub.docker.com/v2/repositories/owasp/zap2docker-bare/",
    }

def collect():
    for key, url in urls.items():
        utils.download_to_file(url, utils.basedir() + "docker/raw/" + utils.today() + '-' + key + ".json")

def daily():
    print("TODO")