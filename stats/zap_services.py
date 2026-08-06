'''
Script for collecting and processing the ZAP service stats
'''
import csv
import utils
import glob
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from collections import defaultdict

aws_region = "us-east-2"
aws_qei = "QueryExecutionId";

# Dates and their string versions
today = datetime.now()
yesterday = today - timedelta(1)
today_str = datetime.strftime(yesterday, '%Y-%m-%d')
this_mon_str = datetime.strftime(today, '%Y-%m')
first = today.replace(day=1)
last_month = first - timedelta(days=1)
last_mon_str = datetime.strftime(last_month, '%Y-%m')

day_raw_file = utils.basedir() + 'cfu/raw/cfu-day-ver-' + today_str + '.csv'
mon_raw_file = utils.basedir() + 'cfu/raw/cfu-mon-ver-' + this_mon_str + '.csv'

day_proc_file = utils.basedir() + 'bitly/daily/cfu-day-ver-' + today_str + '.csv'
mon_proc_file = utils.basedir() + 'bitly/monthly/cfu-mon-ver-' + this_mon_str + '.csv'

# News monthly files are named for the month of activity (not the collection month)
news_mon_raw_file = utils.basedir() + 'news/raw/news-mon-ver-' + last_mon_str + '.csv'
news_mon_proc_file = utils.basedir() + 'news/monthly/news-mon-ver-' + last_mon_str + '.csv'

BITLY_NEWS_PREFIX = 'owaspzap-news-'

# Matches proper ZAP release versions, eg 2.11.0 or a future 3.0.0 - other major
# versions are not expected yet and are treated as invalid for now.
NEWS_VERSION_RE = re.compile(r'^[23]\.\d+\.\d+$')

# Versions with fewer requests than this in a given month are folded into Other,
# to clear out one-off / invalid version strings.
MIN_MONTHLY_REQUESTS = 10

def aws_athena_query(query):
    print('AWS Athena query: ' + query)
    process = subprocess.run(
        ["aws", "athena", "start-query-execution", 
            "--query-string", query, 
            "--work-group", "project-zap",
            "--region", aws_region],
        universal_newlines = True, stdout = subprocess.PIPE)
    res = json.loads(process.stdout)
    if aws_qei in res:
        return res[aws_qei]
    return None

def aws_athena_query_result(id):
    print('AWS Athena query result: ' + id)
    process = subprocess.run(
        ["aws", "athena", "get-query-execution", 
            "--query-execution-id", id,
            "--region", aws_region],
        universal_newlines = True, stdout = subprocess.PIPE)
    #print(process.stdout)
    return json.loads(process.stdout)

def aws_s3_copy(source, dest):
    print('AWS S3 copy: ' + source + ' ' + dest)
    process = subprocess.run(
        ["aws", "s3", "cp", source, dest],
        universal_newlines = True, stdout = subprocess.PIPE)
    print(process.stdout)

def aws_athena_query_to_file(query, file):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    qid = aws_athena_query(query)
    if qid is not None:
        # Loop polling for the result
        for _ in range(100):
            res = aws_athena_query_result(qid)
            if res['QueryExecution']['Status']['State'] == "FAILED":
                print(res)
                break
            if res['QueryExecution']['Status']['State'] == "SUCCEEDED":
                aws_s3_copy(res['QueryExecution']['ResultConfiguration']['OutputLocation'], file)
                break
            time.sleep(5)

def convert_file(source, dest) :
    '''
        Old format: date,link,clicks where link is like '2-11-0' (desktop/cmdline) or '2-11-0d' (daemon)
        New format: date,zapVersion,zaptype,count where zaptype is daemon/desktop/cmdline
    '''
    print ('Processing ' + source + ' to ' + dest + ' minus quotes')
    first = True
    with open(source, 'r') as fs, open(dest, 'w') as fd:
        daily = 0
        for line in fs:
            if first:
                fd.write('date,link,clicks\n')
                first = False
            else:
                (date, ver, type, count) = line.replace('"', '').replace("'", "").split(',')
                valid = True
                if ver.startswith('D-'):
                    daily += int(count.strip())
                    dday = date
                    ver = 'Daily'
                elif ver[1] == '.': # New format
                    ver = ver.replace('.', '-')
                    if type == 'daemon':
                        ver = ver + 'd'
                    fd.write(date + ',' + ver + ',' + count)
        if daily > 0:
            fd.write(dday + ',Daily,' + str(daily) + '\n')

def parse_count(value):
    return int(str(value).replace(',', '').replace('"', '').strip())

def normalize_news_version(ver):
    '''
    Normalize Athena / Bitly news versions for the zap-starts chart (no daemon suffix).
    Only ZAP 2.x/3.x release versions are kept as their own column; anything else
    (SNAPSHOT/custom builds, other major versions, garbled strings) is rolled up
    into 'Other' so they don't each get their own chart column.
    '''
    if ver is None:
        return None
    ver = ver.strip()
    if not ver:
        return None
    if ver.startswith('D-'):
        return 'Daily'
    if ver == 'Dev Build':
        return 'dev'
    if NEWS_VERSION_RE.match(ver):
        return ver.replace('.', '-')
    return 'Other'

def convert_news_file(source, dest):
    '''
    Input: date,zapVersion,count (Athena export; count may use thousands separators)
    Output: date,link,clicks with D-* collapsed to Daily and versions using '-' separators
    '''
    print('Processing news ' + source + ' to ' + dest)
    totals = defaultdict(int)
    with open(source, newline='') as fs:
        reader = csv.DictReader(fs)
        for row in reader:
            if 'date' in row:
                date = row['date'].strip()
                ver = row.get('zapVersion', row.get('zapversion', '')).strip()
                count = parse_count(row['count'])
            else:
                vals = list(row.values())
                date, ver, count = vals[0], vals[1], parse_count(vals[2])
            link = normalize_news_version(ver)
            if link is None:
                continue
            totals[(date, link)] += count

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w', newline='') as fd:
        writer = csv.writer(fd)
        writer.writerow(['date', 'link', 'clicks'])
        for (date, link), count in sorted(totals.items()):
            writer.writerow([date, link, count])

def add_count(data, versions, date, version, count):
    if version not in versions:
        versions.append(version)
    if date not in data:
        data[date] = {}
    data[date][version] = data[date].get(version, 0) + count

def bitly_news_activity_month(date_str):
    '''Bitly monthly rows are dated when collected (early next month); map to activity month.'''
    d = datetime.strptime(date_str[:10], '%Y-%m-%d').replace(day=1)
    prev = d - timedelta(days=1)
    return prev.strftime('%Y-%m-02')

def load_news_monthly(data, versions, exclude_month=None):
    files = sorted(glob.glob(utils.basedir() + 'news/monthly/news-mon-ver-*.csv'))
    used = []
    for file in files:
        with open(file, newline='') as monthly_file:
            reader = csv.DictReader(monthly_file)
            rows = list(reader)
            if not rows:
                continue
            date = rows[0]['date']
            if exclude_month and date.startswith(exclude_month):
                print('Excluding incomplete month from chart: ' + date[:7])
                continue
            used.append(file)
            for row in rows:
                add_count(data, versions, row['date'], row['link'], parse_count(row['clicks']))
    return used

def load_bitly_news(data, versions, before_date=None):
    '''
    Merge historical Bitly news links. Only months strictly before before_date are used
    when Athena news data is present, to avoid double-counting the transition period.
    '''
    files = sorted(glob.glob(utils.basedir() + 'bitly/monthly/*.csv'))
    for file in files:
        with open(file, newline='') as monthly_file:
            reader = csv.reader(monthly_file)
            next(reader, None)
            for row in reader:
                if len(row) < 3:
                    continue
                link = row[1]
                if not link.startswith(BITLY_NEWS_PREFIX):
                    continue
                version = normalize_news_version(link[len(BITLY_NEWS_PREFIX):])
                if version is None:
                    continue
                date = bitly_news_activity_month(row[0])
                if before_date is not None and date >= before_date:
                    continue
                clicks = parse_count(row[3] if len(row) > 3 else row[2])
                add_count(data, versions, date, version, clicks)

def rollup_small_versions(data, versions, threshold=MIN_MONTHLY_REQUESTS):
    '''
    Fold any version with fewer than `threshold` requests in a given month into that
    month's Other bucket, then drop any version column left with no data at all.
    '''
    for counts in data.values():
        for version in [v for v in counts if v != 'Other' and counts[v] < threshold]:
            counts['Other'] = counts.get('Other', 0) + counts.pop(version)

    kept = [v for v in versions if any(counts.get(v, 0) > 0 for counts in data.values())]
    if 'Other' not in kept and any(counts.get('Other', 0) > 0 for counts in data.values()):
        kept.append('Other')
    return kept

def collect():
    # CFU requests by day and version
    aws_athena_query_to_file(
        'SELECT day, zapVersion, zaptype, count(*) as count FROM "AwsDataCatalog"."project_zap_stats"."zap_cfu" WHERE day = \'' + today_str + '\' GROUP BY day, zapVersion, zaptype', 
        day_raw_file)
    
    # CFU requests by month and version
    if not os.path.isfile(mon_raw_file):
        # For historical reasons the monthly stats are collected on the 2nd of the next month
        aws_athena_query_to_file(
            'SELECT \'' + this_mon_str + '-02\', zapVersion, zaptype, count(*) as count FROM "AwsDataCatalog"."project_zap_stats"."zap_cfu" WHERE day LIKE \'' + last_mon_str + '-%\' GROUP BY zapVersion, zaptype', 
            mon_raw_file)

    # News requests by month and version (month of activity). Only collect once the month is complete.
    if today.day >= 2 and not os.path.isfile(news_mon_raw_file):
        aws_athena_query_to_file(
            'SELECT \'' + last_mon_str + '-02\', zapVersion, count(*) as count FROM "AwsDataCatalog"."project_zap_stats"."zap_news" WHERE day LIKE \'' + last_mon_str + '-%\' GROUP BY zapVersion',
            news_mon_raw_file)

def daily():
    # The raw files need to be processed to match the 'old' expected format
    
    # CFU requests by day and version
    convert_file(day_raw_file, day_proc_file)

    # CFU requests by month and version
    if not os.path.isfile(mon_proc_file):
        convert_file(mon_raw_file, mon_proc_file)

    # News monthly (immutable once written)
    if os.path.isfile(news_mon_raw_file) and not os.path.isfile(news_mon_proc_file):
        convert_news_file(news_mon_raw_file, news_mon_proc_file)

def backfill():
    '''
    One-time ingest of a full Athena news export into news/monthly/*.csv files.
    Usage: python zap_services.py backfill [path-to-news.csv]
    Existing monthly files are left unchanged.
    '''
    if len(sys.argv) >= 3:
        source = sys.argv[2]
    else:
        source = os.path.join(os.path.dirname(__file__), '../../zap-stats/news.csv')
    source = os.path.abspath(source)
    if not os.path.isfile(source):
        print('Backfill source not found: ' + source)
        return

    print('Backfilling news monthly files from ' + source)
    by_month = defaultdict(list)
    with open(source, newline='') as fs:
        reader = csv.DictReader(fs)
        for row in reader:
            date = row['date'].strip()
            month = date[:7]
            by_month[month].append(row)

    raw_dir = utils.basedir() + 'news/raw/'
    mon_dir = utils.basedir() + 'news/monthly/'
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(mon_dir, exist_ok=True)

    for month in sorted(by_month.keys()):
        if month >= this_mon_str:
            print('Skipping incomplete month in backfill: ' + month)
            continue
        raw_file = raw_dir + 'news-mon-ver-' + month + '.csv'
        proc_file = mon_dir + 'news-mon-ver-' + month + '.csv'
        if os.path.isfile(proc_file):
            print('Skipping existing ' + proc_file)
            continue
        with open(raw_file, 'w', newline='') as fd:
            writer = csv.DictWriter(fd, fieldnames=['date', 'zapVersion', 'count'])
            writer.writeheader()
            for row in by_month[month]:
                writer.writerow({
                    'date': row['date'].strip(),
                    'zapVersion': row['zapVersion'].strip(),
                    'count': parse_count(row['count']),
                })
        convert_news_file(raw_file, proc_file)
        print('Wrote ' + proc_file)

def website():
    '''Generate the zap-starts stacked bar chart from news monthly + historical Bitly news.'''
    outfile = utils.websitedir() + 'site/data/charts/zap-starts.json'
    data = {}
    versions = []

    # Current calendar month is incomplete until the next month's collection runs
    news_files = load_news_monthly(data, versions, exclude_month=this_mon_str)
    earliest_news = min(data.keys()) if data else None
    load_bitly_news(data, versions, before_date=earliest_news)

    if not data:
        print('No news data found for zap-starts chart')
        return

    versions = rollup_small_versions(data, versions)

    with open(outfile, 'w') as f:
        print('{', file=f)
        print('  "title": "ZAP Starts",', file=f)
        print('  "description": "The number of News requests ZAP made per month, by version. These are a good approximation of the number of times ZAP was started. Daily/weekly builds are grouped under Daily.",', file=f)
        print('  "columns": ["Version"', end='', file=f)
        for l in versions:
            print(', "' + l + '"', end='', file=f)
        print('],', file=f)
        print('  "data": [', end='', file=f)

        first = True
        for date in sorted(data.keys()):
            if not first:
                print(',', end='', file=f)
            else:
                first = False
            print('\n    ["' + date[:-2] + '01"', end='', file=f)
            for l in versions:
                print(', ' + str(data[date].get(l, 0)), end='', file=f)
            print(', ""]', end='', file=f)

        print('\n  ]', file=f)
        print('}', file=f)

    print('Updated: ' + outfile + ' from ' + str(len(news_files)) + ' news monthly files')

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        fn = sys.argv[1]
        if fn in globals():
            globals()[fn]()
        else:
            print('Unknown command: ' + fn)
    else:
        print('Usage: zap_services.py collect|daily|website|backfill [news.csv]')
