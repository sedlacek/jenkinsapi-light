from ast import literal_eval
import time
from jenkinsapi.misc import JenkinsApiRequestFailed, join_url
from jenkinsapi.requester import JenkinsAuth, Requester

__author__ = 'sedlacek'


class JenkinsBase(object):

    API = 'api/python'

    def __init__(self, url, poll_interval=None, auth=JenkinsAuth(), timeout=None):
        """

        :param auth:                jenkins auth - either apitoken or username and pwd
        :param timeout:             timeout for API calls
        :param url:                 jenkins URL, api/python will be added to the end
        :param poll_interval:       0 - data polled always when value requested
                                    >0 - interval in which data are refreshed (in seconds)
                                    None - data automatically polled only once, when data are accessed
        """
        self._timeout = timeout
        self._url = url
        self._poll_interval = poll_interval
        self._next_poll = 0                                 # 0 if we never polled the data
        self._data = {}                                     # empty jenkins data, should be populated by self.poll
        self._auth = auth                                   # jenkins authentication object, either token or BasicAuth
        self._requester = None                              # requester, setup at first poll request
        if self._poll_interval is not None:
            self.poll()

    def poll(self):
        """
        Poll jenkins data, honor poll interval accordingly
        """
        now = time.time()
        if self._poll_interval is None:
            self._poll()
            self._next_poll = now
        else:
            if self._next_poll <= now:
                self._poll()
                self._next_poll = now + self._poll_interval
        return self

    def auto_poll(self):
        """
        If requested automatically refresh data, should be used in each data call
        """
        if self._poll_interval is not None or self._next_poll == 0:
            return self.poll()
        else:
            return self

    @property
    def requester(self):
        if self._requester is None:
            if self._auth.token is not None:
                params = {'token': self._auth.token}
            else:
                params = {}
            self._requester = Requester(url=self._api_url, params=params,
                                        username=self._auth.auth.username, password=self._auth.auth.password,
                                        timeout=self.timeout)
        return self._requester

    def _poll(self):
        """
        Real poll worker, if needed should be overridden in inherited classes
        """
        response = self.requester.get()
        if response.status_code != 200:
            raise JenkinsApiRequestFailed('Request (%s) failed %d %s for %s' % ('GET', response.status_code, response.reason, response.url))
        self._update_data(literal_eval(response.content))
        return self

    def _update_data(self, data):
        """
        Data update, should be overridden in subclasses
        """
        self._data.update(data)

    # RO access to private properties
    @property
    def url(self):
        return self._url

    @property
    def poll_interval(self):
        return self._poll_interval

    @property
    def auth(self):
        return self._auth

    @property
    def timeout(self):
        return self._timeout

    @property
    def _api_url(self):
        """
        Could be perhaps done more efficiently ...
        :return:    Jenkins API URL
        """
        return join_url(self._url, self.API)

    # expose data as dictionary
    def __len__(self):
        self.auto_poll()
        return self._data.__dict__.__len__()

    def __getitem__(self, item):
        self.auto_poll()
        return self._data.__dict__.__getitem__(item)

    def __setitem__(self, key, value):
        return self._data.__dict__.__setitem__(key, value)

    def __delitem__(self, key):
        return self._data.__dict__.__delitem__(key)

    def __iter__(self):
        self.auto_poll()
        return self._data.__dict__.__iter__()

    def __contains__(self, item):
        self.auto_poll()
        return self._data.__dict__.__contains__(item)

    def get(self, key, default=None):
        self.auto_poll()
        return self._data.get(key, default)

    @property
    def data(self):
        self.auto_poll()
        return self._data