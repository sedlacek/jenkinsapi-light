import requests

from collections import namedtuple
from jenkinsapi.misc import default, merge_all_dict, last_not_none

__author__ = 'sedlacek'

_JenkinsAuth = namedtuple('JenkinsAuth', ('token', 'auth'))
_SimpleAuth = namedtuple('SimpleAuth', ('username', 'password'))


class SimpleAuth(object):
    def __new__(cls, username=None, password=None):
        return _SimpleAuth(username=username, password=password)


class JenkinsAuth(object):
    def __new__(cls, token=None, username=None, password=None):
        return _JenkinsAuth(token=token, auth=SimpleAuth(username=username, password=password))


class Requester(object):
    """
    Object requesting data
    """
    def __init__(self, url, username=None, password=None, params=None, headers=None, cookies=None, timeout=None):
        self._url = url
        self._auth = ()
        if username is not None:
            self._auth = SimpleAuth(username=username)
            if password is not None:
                self._auth = SimpleAuth(username=username, password=password)

        self._timeout = timeout
        self._params = default(params, {})
        self._headers = default(headers, {})
        self._cookies = default(cookies, {})

    def get(self, url=None, params=None, headers=None, cookies=None, auth=None):
        print 'GET: %s' % default(url, self._url)
        request = requests.get(
            url=default(url, self._url),
            params=merge_all_dict(self._params, params),
            cookies=merge_all_dict(self._cookies, cookies),
            headers=merge_all_dict(self._headers, headers),
            auth=last_not_none(self._auth, auth),
            timeout=self._timeout)
        return request

    def post(self, url=None, params=None, data=None, headers=None, cookies=None, auth=None, files=None):
        print 'POST: %s' % default(url, self._url)
        request = requests.post(
            url=default(url, self._url),
            params=merge_all_dict(self._params, params),
            cookies=merge_all_dict(self._cookies, cookies),
            headers=merge_all_dict({'Content-Type': 'application/x-www-form-urlencoded'}, self._headers, headers),
            auth=last_not_none(self._auth, auth),
            data=last_not_none('', data),
            files=files,
            timeout=self._timeout
        )
        return request

    def update_headers(self, value):
        self._headers.update(value)
        return self

    def update_cookies(self, value):
        self._cookies.update(value)
        return self

    def update_params(self, value):
        self._params.update(value)
        return self