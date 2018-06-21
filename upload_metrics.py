import argparse
import sys
import urllib2


APP_URL = 'https://cit-cli-metrics.appspot.com'


def main():
  urllib2.urlopen(APP_URL + '/upload', sys.argv[1])

  return 0


if __name__ == '__main__':
  sys.exit(main())
