__author__ = 'sedlacek'

from jenkinsapi.jenkins import Jenkins
from jenkinsapi.jenkinsjob import JenkinsJob
from jenkinsapi.requester import JenkinsAuth
import logging


import argparse
from ast import literal_eval

parser = argparse.ArgumentParser(description='Build a Job')
parser.add_argument('--jenkins', required=True, metavar='<jenkins>', help='jenkins url')
parser.add_argument('--user', required=False, default=None, metavar='<user>', help='jenkins user')
parser.add_argument('--password', required=False, default=None, metavar='<password>', help='user password or API token')
parser.add_argument('--job', required=True, metavar='<job>', help='job name')
parser.add_argument('--token', required=False, default=None,  metavar='<token>', help='job\'s API token')
parser.add_argument('--block', action='store_true', help='wait until build finish.')
parser.add_argument('--console', action='store_true', help='implies block - copy console output to stdout')
parser.add_argument('--cause', required=False, default=None,  metavar='<cause>', help='build cause')
parser.add_argument('--level', required=False, default='WARNING',  metavar='<debug level>', help='Debug Level')
parser.add_argument('params', metavar='param1=value', nargs='*', help='build parameters, file type paramenter is not supported yet')


args = vars(parser.parse_args())

logging.getLogger().setLevel(args['level'])

jenkins = Jenkins(url=args['jenkins'], auth=JenkinsAuth(username=args['user'], password=args['password'], token=args['token']))
job = JenkinsJob(parent=jenkins, objid=args['job'])

params = {}
for param in args['params']:
    key, value = param.split('=', 1)
    params[key] = literal_eval(value)
if len(params) == 0:
    params = None

block = args['block']
console = args['console']

if console:
    # we have to wait for job to finish
    block = True

qitem = job.enqueue_build(cause=args['cause'], params=params)
logging.info('Job enqueued as queue item %s' % qitem.url)

if block:
    # wait for build to be dequeued
    logging.debug('Waiting for build to be dequeued')
    qitem.block()
    logging.debug('Build dequeued.')
else:
    # we do not wait for anything, so exit in any case
    exit(0)

build = qitem.build

if build is not None:
    build.poll()
else:
    logging.error('Build perhaps cancelled while has been in the queue.')
    # queue item has been probably cancelled :(
    exit(1)

if console:
    for line in build.console(reset=True, poll_interval=1):
        print line

    assert not build.poll().isbuilding,\
        'Something wrong happened, build is still building, ' \
        'but console polling does not have more data :('
else:
    logging.debug('Waiting for build to finish')
    build.block()

if not build.ok:
    logging.error('Build finished with status %s' % build['result'])
    exit(10)

logging.info('Build finished with status %s' % build['result'])