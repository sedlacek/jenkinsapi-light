__author__ = 'sedlacek'

from jenkinsapi.jenkins import Jenkins
from jenkinsapi.jenkinsjob import JenkinsJob
from jenkinsapi.requester import JenkinsAuth

import re

import logging

logging.basicConfig()
logger = logging.getLogger(__file__)

import argparse


class OpenFiles(object):
    """
    Context manager opening all files and making sure that in the end all are closed ...
    """
    def __init__(self, files, mode='rb'):
        """
        :param dict files:      dict {paramname: filename}
        :param str mode:        mode, default 'rb'
        :return dict:           dictionary containing open files  {paramname: file}
        """
        self._files = dict(files)
        self._mode = mode
        self._openfiles = {}

    def __enter__(self):
        """
        Open all files
        :return dict:           dictionary containing open files  {paramname: file}
        """
        self._openfiles = {key: open(value, self._mode) for key, value in self._files.iteritems()}
        # intentionally making a copy - we do not want having some files accidentally removed from dict
        return dict(self._openfiles)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        close all files
        """
        for openfile in self._openfiles.itervalues():
            try:
                openfile.close()
            except Exception:
                pass
        # make sure exceptions are handled upstream
        return False


class RegExFilter(object):
    """
    Callable for filtering out unwanted atrifacts
    """
    def __init__(self, regex):
        """
        :param regex:   regular expression
        """
        try:
            self._regex = re.compile(regex)
        except Exception as e:
            # broken regex
            e.message += '\nInvalid Regular Expression'
            raise e

    def __call__(self, string):
        """
        if string match regex return true

        :param str|unicode string:      string to be matched
        :return re.MatchObject|bool:
        """
        return self._regex.search(string)

parser = argparse.ArgumentParser(description='Build a Job')
parser.add_argument('--jenkins', required=True, metavar='<jenkins>', help='jenkins url')
parser.add_argument('--user', required=False, default=None, metavar='<user>', help='jenkins user')
parser.add_argument('--password', required=False, default=None, metavar='<password>', help='user password or API token')
parser.add_argument('--job', required=True, metavar='<job>', help='job name')
parser.add_argument('--token', required=False, default=None,  metavar='<token>', help='job\'s API token')
parser.add_argument('--prefix', required=False, default='remote> ',  metavar='<prefix>', help='output prefix')
parser.add_argument('--noblock', action='store_true', help='do not wait until build finish.')
parser.add_argument('--noconsole', action='store_true', help='do no copy console output to stdout')
parser.add_argument('--cause', required=False, default=None,  metavar='<cause>', help='build cause')
parser.add_argument('--level', required=False, default='WARNING',  metavar='<debug level>', help='Debug Level')
parser.add_argument('--artifacts', required=False, default=None, metavar='<artifacts>', help='Artifacts to download (regex) or ALL')
parser.add_argument('params', metavar='param1=value', nargs='*', help='build parameters, file type param2=@filename')


args = vars(parser.parse_args())

logger.setLevel(args['level'])

jenkins = Jenkins(url=args['jenkins'], auth=JenkinsAuth(username=args['user'], password=args['password'], token=args['token']))
job = JenkinsJob(parent=jenkins, objid=args['job'])

params = {}
files = {}
for param in args['params']:
    key, value = param.split('=', 1)
    if value.startswith('@'):
        files[key] = value[1:]
    else:
        params[key] = value
if len(params) == 0:
    params = None

block = not args['noblock']
console = not args['noconsole']

if console:
    # we have to wait for job to finish
    block = True

if files != {}:
    with OpenFiles(files, mode='rb') as openfiles:
        qitem = job.enqueue_build(cause=args['cause'], params=params, files=openfiles)
else:
    qitem = job.enqueue_build(cause=args['cause'], params=params)
logger.info(' Job enqueued as queue item %s' % qitem.url)

if block:
    # wait for build to be dequeued
    logger.debug(' Waiting for build to be dequeued')
    qitem.block()
    logger.debug(' Build dequeued.')
else:
    # we do not wait for anything, so exit in any case
    exit(0)

build = qitem.build

if build is not None:
    build.poll()
else:
    logger.error(' Build perhaps cancelled while has been in the queue.')
    # queue item has been probably cancelled :(
    exit(1)

if console:
    for line in build.console(reset=True, poll_interval=1):
        print '%s%s' % (args['prefix'], line)

    assert not build.poll().isbuilding,\
        'Something wrong happened, build is still building, ' \
        'but console polling does not have more data :('
else:
    logger.debug(' Waiting for build to finish')
    build.block()

if args['artifacts'] is not None:
    # download artifacts
    if args['artifacts'] == 'ALL':
        _artifacts = None
    else:
        _artifacts = RegExFilter(args['artifacts'])

    build.artifacts.writeall(filter_artifacts=_artifacts)

if not build.ok:
    logger.error(' Build finished with status %s' % build['result'])
    exit(10)

logger.info(' Build finished with status %s' % build['result'])