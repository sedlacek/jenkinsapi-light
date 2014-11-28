import requests

from jenkinsapi.misc import default, merge_all_dict, last_not_none
import logging

__author__ = 'sedlacek'

class SimpleAuth(object):

    def __init__(self, username=None, password=None):
        assert (username is not None) or (username is None and password is None),\
            'Cannot have password without username!'
        self._username = username
        self._password = password

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    def __getitem__(self, key):
        if key == 0:
            return self.username
        elif key == 1:
            return self.password
        else:
            raise IndexError('Index out of range.')

    def __iadd__(self, other):
        """
        Try to merge auth in clever way
        """
        assert isinstance(other, SimpleAuth), 'I know how to deal only with %s objects' % self.__class__.__name__
        if self.username is None and other.username is not None:
            self._username = other.username
        assert self.username == other.username, 'I cannot change username :('
        if self.username is not None and other.username is not None and other.password is not None:
            self._password = other.password
        return self

    def __eq__(self, other):
        assert isinstance(other, SimpleAuth), 'I can compare only %s objects' % self.__class__.__name__
        return self.username == other.username and self.password == other.password


class JenkinsAuth(object):

    def __init__(self, token=None, username=None, password=None):
        self._auth = SimpleAuth(username=username, password=password)
        self._token = token

    @property
    def auth(self):
        return self._auth

    @property
    def token(self):
        return self._token

    def __iadd__(self, other):
        """
        merge authentications,
        """
        assert isinstance(other, JenkinsAuth), 'I know how to deal only with %s objects' % self.__class__.__name__
        if other.token is not None:
            self._token = other.token
        self._auth += other.auth
        return self

    def __getitem__(self, key):
        if key == 0:
            return self.token
        elif key == 1:
            return self.auth
        else:
            raise IndexError('Index out of range.')

    def __eq__(self, other):
        assert isinstance(other, JenkinsAuth), 'I can compare only %s objects' % self.__class__.__name__
        return self.token == other.token and self.auth == other.auth


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
        logging.debug('GET: %s' % default(url, self._url))
        request = requests.get(
            url=default(url, self._url),
            params=merge_all_dict(self._params, params),
            cookies=merge_all_dict(self._cookies, cookies),
            headers=merge_all_dict(self._headers, headers),
            auth=last_not_none(self._auth, auth),
            timeout=self._timeout)
        return request

    def post(self, url=None, params=None, data=None, headers=None, cookies=None, auth=None, files=None):
        logging.debug('POST: %s\n\tparams: %s\n\tdata: %s' % (default(url, self._url), str(params), str(data)))
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