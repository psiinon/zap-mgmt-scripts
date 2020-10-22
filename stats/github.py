'''
Script for collecting and processing the ZAP docker stats
'''
import utils
import glob
import json
import os
import sys

tags = [
    "v2.9.0",
    "v2.8.0",
    ]

mappings = {
  "core": "core",
  "crossplatform": "cross",
  "linux": "linux",
  "unix": "unix",
  "deb": "deb",
  "dmg": "mac",
  "windows-x32": "win32",
  "windows.exe": "win64",
}

github_api = "https://api.github.com/repos/zaproxy/zaproxy/releases/tags/"

def collect():
    for tag in tags:
        utils.download_to_file(github_api + tag, utils.basedir() + "downloads/raw/" + utils.today() + '-' + tag + ".json")

def daily():
    # Process the download stats
    counts = {}
    assets = {}
    files = sorted(glob.glob(utils.basedir() + "downloads/raw/*.json"))
    for file in files:
        with open(file) as stats_file:
            stats = json.load(stats_file)
            date_str = os.path.basename(stats_file.name)[:10]
            daily_file = utils.basedir() + 'downloads/daily/' + date_str + '.csv'
            file_exists = os.path.exists(daily_file)
            if not file_exists:
                with open(daily_file, "a") as f:
                    print('Creating ' + daily_file)
                    f.write('date,version,name,count,downloads\n')
            for asset in stats['assets']:
                name = asset['name']
                count = asset['download_count']
                if (name in counts):
                    # Ignore negative numbers - can happen when files are replaced
                    old_count = counts[name]
                else:
                    old_count = 0
                if (name in counts):
                    # Ignore negative numbers - can happen when files are replaced
                    assets[name] = max((count - counts[name]), 0)
                else:
                    assets[name] = count
                counts[name] = count
                mapping = "Unknown"
                for m in mappings:
                    if m in name.lower():
                        mapping = mappings[m]
                        break
                
                if old_count > 0:
                    if not file_exists:
                        with open(daily_file, "a") as f:
                            f.write(date_str + ',' +  stats['name'] + ',' + asset['name'] + ',' + mapping + ',' + str(assets[name]) + '\n')
