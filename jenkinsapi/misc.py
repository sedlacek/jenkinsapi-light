__author__ = 'sedlacek'

from collections import namedtuple

# Job in context of Jenkins
RefJob = namedtuple('RefJob', ('jenkins', 'name'))
# Build in context of a Job
RefBuild = namedtuple('RefBuild', ('job', 'number'))
# Queue in context of the jenkins
RefQueue = namedtuple('RefQueue', ('jenkins', ))
# QueueItem in context of the queue
RefQueueItem = namedtuple('RefQueueItem', ('queue', 'itemid'))

def default(value, default_if_value_is_None):
    """
    Returns default value is value is None
    """
    if value is None:
        return default_if_value_is_None
    else:
        return value


def merge_all_dict(*args):
    """
    Merges all dictionaries into new empty one, if arg is None, it is skipped ...
    """
    res = {}
    for arg in args:
        if arg is not None:
            res.update(arg)
    return res


def last_not_none(*args):
    """
    Returns last not None argument
    """
    res = None
    for arg in args:
        if arg is not None:
            res = arg
    return res


def join_url(*args):
    """
    :param args:        url snippets
    :return:            blindly joined url by a '/'
    """
    res = []
    for arg in args:
        if arg is None:
            continue
        res.append(normalize_url(arg))
    return '/'.join(res)


def normalize_url(url_):
    """
    Removes last '/' if it is last character ...
    """
    url = str(url_)
    if url[-1] == '/':
        return url[:-1]
    else:
        return url


class JenkinsApiRequestFailed(Exception): pass