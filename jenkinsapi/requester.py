import requests
import ssl
from time import sleep
from OpenSSL.SSL import ZeroReturnError

from jenkinsapi.misc import default, merge_all_dict, last_not_none

import logging
logger = logging.getLogger(__name__)

__author__ = 'sedlacek@avast.com'

# workaround for not so reliable connection
RETRIES = 5             # Number of retries for connection problems
RETRY_WAIT = 5          # wait in seconds between each retry

# workaround for broken ssl in python :(
SSLVers = []
SSLVersStr = {None: 'UNKNOWN'}
# lets try to get highest possible SSL version
try:
    SSLVers.insert(0, ssl.PROTOCOL_SSLv2)
    SSLVersStr[ssl.PROTOCOL_SSLv2] = 'SSLv2'
except:
    pass
try:
    SSLVers.insert(0, ssl.PROTOCOL_SSLv3)
    SSLVersStr[ssl.PROTOCOL_SSLv3] = 'SSLv3'
except:
    pass
try:
    SSLVers.insert(0, ssl.PROTOCOL_SSLv23)
    SSLVersStr[ssl.PROTOCOL_SSLv23] = 'SSLv23'
except:
    pass
try:
    SSLVers.insert(0, ssl.PROTOCOL_TLSv1)
    SSLVersStr[ssl.PROTOCOL_TLSv1] = 'TLSv1'
except:
    pass
try:
    SSLVers.insert(0, ssl.PROTOCOL_TLSv1_1)
    SSLVersStr[ssl.PROTOCOL_TLSv1_1] = 'TLSv1_1'
except:
    pass
try:
    SSLVers.insert(0, ssl.PROTOCOL_TLSv1_2)
    SSLVersStr[ssl.PROTOCOL_TLSv1_2] = 'TLSv1_2'
except:
    pass

logger.debug(' Detected SSL versions: %s' % str(SSLVersStr.values()))

# from https://lukasa.co.uk/2013/01/Choosing_SSL_Version_In_Requests/
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

class SSLAdapter(HTTPAdapter):
    '''An HTTPS Transport Adapter that uses an arbitrary SSL version.'''
    def __init__(self, ssl_version=None, **kwargs):
        self.ssl_version = ssl_version

        super(SSLAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=self.ssl_version)

# end of from https://lukasa.co.uk/2013/01/Choosing_SSL_Version_In_Requests/

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
    def __init__(self, url, username=None, password=None, params=None, headers=None,
                 cookies=None, timeout=None, session=None):
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

        if session is None:
            # create request session object and try to auto detect proper ssl version
            self._session = requests.session()
            if self._url.startswith('https://'):
                SSLVer = None
                for SSLVer in SSLVers:
                    try:
                        self._session = requests.session()
                        self._session.mount('https://', SSLAdapter(SSLVer))
                        self._session.get(self._url)
                        break
                    except requests.exceptions.SSLError:
                        continue
                logger.debug('Detected SSL Version: %s' % SSLVersStr[SSLVer])
        else:
            self._session = session

    def get(self, url=None, params=None, headers=None, cookies=None, auth=None):
        logger.debug('GET: %s' % default(url, self._url))
        # workaround for unreliable network and servers, giwe it few retries

        for i in range(RETRIES):
            try:
                request = self._session.get(
                    url=default(url, self._url),
                    params=merge_all_dict(self._params, params),
                    cookies=merge_all_dict(self._cookies, cookies),
                    headers=merge_all_dict(self._headers, headers),
                    auth=last_not_none(self._auth, auth),
                    timeout=self._timeout)
            except ZeroReturnError:
                sleep(RETRY_WAIT)
                continue
            except:
                # other error, just re-rise
                raise
            # all ok, so continue
            break

        if not request.ok:
            raise IOError('HTTPStatus: %s\nCannot get %s.' % (request.status_code, url))
        logger.debug('GET:response: %s' % request.content)
        return request

    def iterget(self, url=None, params=None, headers=None, cookies=None, auth=None, blocksize=None):

        logger.debug('GET_(iterator): %s' % default(url, self._url))

        if blocksize is None:
            # lets try 1kB chunks
            blocksize = 1024

        for i in range(RETRIES):
            try:
                request = self._session.get(
                    url=default(url, self._url),
                    params=merge_all_dict(self._params, params),
                    cookies=merge_all_dict(self._cookies, cookies),
                    headers=merge_all_dict(self._headers, headers),
                    auth=last_not_none(self._auth, auth),
                    timeout=self._timeout,
                    stream=True)
            except ZeroReturnError:
                sleep(RETRY_WAIT)
                continue
            except:
                # other error, just re-rise
                raise
            # all ok, so continue
            break

        if not request.ok:
            raise IOError('HTTPStatus: %s\nCannot get %s.' % (request.status_code, url))
        logger.debug('GET_(iterator):response: %s' % 'OK')
        return request.iter_content(blocksize)

    def post(self, url=None, params=None, data=None, headers=None, cookies=None, auth=None, files=None):
        logger.debug('POST: %s' % default(url, self._url))
        logger.debug('POST:params: %s' % str(params))
        logger.debug('POST:data: %s' % str(data))
        request = self._session.post(
            url=default(url, self._url),
            params=merge_all_dict(self._params, params),
            cookies=merge_all_dict(self._cookies, cookies),
            #headers=merge_all_dict({'Content-Type': 'multipart/form-data'}, self._headers, headers),
            headers=merge_all_dict({'Content-Type': 'application/x-www-form-urlencoded'} if files is None else None, self._headers, headers),
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

    @property
    def session(self):
        return self._session