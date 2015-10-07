__author__ = 'sedlacek'

# constants

DEFAULT_POLL_INTERVAL = 5           # polling interval default for blocking operations
                                    # I do not know about any other method how to get jenkins data on change
                                    # then regular polling :(

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
        if arg is None or arg == '':
            continue
        res.append(normalize_url(arg))
    return '/'.join(res)


def normalize_url(url_):
    """
    Removes last '/' if it is last character ...
    """
    if url_ is None:
        return None
    url = str(url_)
    if url[-1] == '/':
        return url[:-1]
    else:
        return url


class IgnoreKeyError(object):

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type == KeyError:
            return True


class JenkinsApiRequestFailed(Exception): pass
class JenkinsNotAvailable(Exception): pass
class JenkinsNoMoreConsoleData(Exception): pass

