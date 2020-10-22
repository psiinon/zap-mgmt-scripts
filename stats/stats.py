# Local files which handle specific stats
import docker
import github
# Python imports
import os
import sys

def usage():
    print("stats.py collect | daily | monthly")

def collect():
    docker.collect()
    github.collect()

def daily():
    docker.daily()
    github.daily()

if __name__ == '__main__':
    if len(sys.argv) == 2:
        fn = sys.argv[1]
        if fn in globals():
            globals()[sys.argv[1]]()
        else:
            usage()
    else:
        usage()
