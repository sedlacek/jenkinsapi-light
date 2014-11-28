from ast import literal_eval
import time
import jenkinsapi.misc
import jenkinsapi.requester
import jenkinsapi.jenkins

__author__ = 'sedlacek'


class FakeJenkinsBase(object):
    """
    Class for sparse Jenkins object currently providing only url and does not allow cascading of jenkins objects
    """

    def __init__(self, url):
        self._url = jenkinsapi.misc.normalize_url(url)

    @property
    def url(self):
        return self._url

    def __getattr__(self, item):
        raise NotImplementedError('You should cascade API classes properly to be able access parent\'s object "%s"' % item)


class JenkinsBase(object):

    _API = 'api/python'
    _EXTRA = None            # parent_url/EXTRA/objid

    def __init__(self, parent=None, objid=None, url=None, data=None, poll_interval=None,
                 auth=None, timeout=None):
        """
        :param parent:              parent jenkins object
        :param objid:               object id in parent context
        :param url:                 jenkins URL, api/python will be added to the end
        :param data:                we already got the data, so initiate the object with the data
        :param auth:                jenkins auth - either apitoken or username and pwd
        :param timeout:             timeout for API calls
        :param url:                 jenkins URL, api/python will be added to the end
        :param poll_interval:       0 - data polled always when value requested
                                    >0 - interval in which data are refreshed (in seconds)
                                    None - data automatically polled only once, when data are accessed
        """

        assert (parent is None and objid is None and url is not None)\
            or (parent is not None and objid is not None and url is None)\
            or (parent is not None and objid is None and url is not None),\
            'Unsupported combination of arguments: parent, objid and url.'

        if auth is None:
            auth = jenkinsapi.requester.JenkinsAuth()

        self._url = jenkinsapi.misc.normalize_url(url)
        self.objid = objid
        self._parent = parent

        if self._parent is None:
            _ = self.parent                                 # force self._parent creation (FakeJenkinsBase)
        if self._url is None:
            _ = self.url                                    # force self_url creation from parent and objid

        self._timeout = timeout
        self._poll_interval = poll_interval
        self._next_poll = 0                                 # 0 if we never polled the data
        self._last_poll = 0                                 # 0 if we never polled the data
        self._data = {}                                     # empty jenkins data, should be populated by self.poll
        self._auth = auth                                   # jenkins authentication object, either token or BasicAuth
        self._requester = None                              # requester, setup at first poll request

        if self._poll_interval is not None or data is not None:
            self.poll(data)

        self._api = None                                    # api url

    def __an_update__(self, poll_interval=None, auth=None, timeout=None):
        """
        Update values of poll_interval, auth and timeout
        :param poll_interval:               if new poll interval is shorter, then update it
        :param auth:                        if auth is more specific, then update it, or set new token
        :param timeout:                     if new timeout is shorter, then update it
        :return:                            None
        """
        if auth is None:
            auth = jenkinsapi.requester.JenkinsAuth()
        # we should merge auth
        self.auth += auth
        # choose shorter timeout
        if self.timeout < timeout:
            self.timeout = timeout
        # choose shorter poll_interval
        if self.poll_interval < poll_interval:
            self.poll_interval = poll_interval
        # and allow easy chaining ....
        return self

    def poll(self, data=None, now=None):
        """
        Poll jenkins data, honor poll interval accordingly
        :param now:             set poll timestamp
        :param data:            instead of polling from server use data
        """
        if now is None:
            now = time.time()
        if data is not None:
            # we already have data, so use them for update
            self._update_data(data=data, now=now)
            self._update_poll(now)
        elif self._poll_interval is None or self._next_poll <= now:
            self._poll()
            self._update_poll(now)
        return self

    def auto_poll(self):
        """
        If requested automatically refresh data, should be used in each data call
        """
        if self._poll_interval is not None or self._next_poll == 0:
            return self.poll()
        else:
            return self

    def purge(self):
        """
        Clean all data and retrieve complete new set from jenkins
        """
        self._data = {}
        self._next_poll = 0
        self._last_poll = 0

    def _update_poll(self, epoch):
        """
        Updating poll timestamps
        :return:            next poll time
        """
        self._last_poll = epoch
        self._next_poll = epoch if self._poll_interval is None else epoch + self._poll_interval
        return self._next_poll

    @property
    def requester(self):
        if self._requester is None:
            if self._auth.token is not None:
                params = {'token': self.auth.token}
            else:
                params = {}
            self._requester = jenkinsapi.requester.Requester(url=self.api, params=params,
                                        username=self.auth.auth.username, password=self.auth.auth.password,
                                        timeout=self.timeout)
        return self._requester

    def _poll(self):
        """
        Real poll worker, if needed should be overridden in inherited classes
        """
        response = self.requester.get()
        if response.status_code != 200:
            raise jenkinsapi.misc.JenkinsApiRequestFailed('Request (%s) failed %d %s for %s' % ('GET', response.status_code, response.reason, response.url))
        self._update_data(literal_eval(response.content))
        return self

    def _update_data(self, data, now=None):
        """
        Data update, should be overridden in subclasses
        :param now:     update timestamp
        """
        # just mirror what is available in jenkins
        self._data = data

    @staticmethod
    def objid_from_url(url):
        return jenkinsapi.misc.normalize_url(url).split('/')[-1]

    @property
    def objid(self):
        """
        :return:            jenkins object ID
        """
        if self._objid is not None:
            return self._objid
        if self._url is not None:
            self._objid = self.objid_from_url(self._url)
            return self._objid
        raise ValueError('Cannot guess objid')

    @objid.setter
    def objid(self, value):
        """
        objid is always converted to string
        """
        if value is None:
            self._objid = None
        else:
            self._objid = str(value)

    @property
    def parent(self):
        """
        :return:            parent object, either real Jenkins API object or Fake one
        """
        if self._parent is not None:
            return self._parent
        if self._url is not None:
            self._parent = FakeJenkinsBase(jenkinsapi.misc.normalize_url(self.url)[: -1 - len(self.objid) - 0 if self._EXTRA is None else (1 + len(self._EXTRA))])
            return self._parent
        raise ValueError('Cannot guess parent API object.')

    @property
    def jenkins(self):
        """
        :return:            Jenkins object instance or None if it could not be found
        """
        # is  self._jenkins is defined, then return self._jenkins
        if hasattr(self,'_jenkins'):
            return self._jenkins
        # now traverse all parents up to the root and return first which is instance of Jenkins
        parent = self
        while not isinstance(parent, jenkinsapi.jenkins.Jenkins):
            parent = parent.parent
            if isinstance(parent, FakeJenkinsBase):
                # ok, we cannot fond Jenkins instance :(
                break
        if isinstance(parent, jenkinsapi.jenkins.Jenkins):
            self._jenkins = parent
            return parent
        else:
            self._jenkins = None
            return None

    @property
    def url(self):
        """
        :return:            my own url
        """
        if self._url is not None:
            return self._url
        if self.parent is not None and self.objid is not None:
            self._url = jenkinsapi.misc.normalize_url(jenkinsapi.misc.join_url(self.parent.url, self._EXTRA, self.objid))
            return self._url
        raise ValueError('Cannot guess URL.')

    @property
    def poll_interval(self):
        return self._poll_interval

    @poll_interval.setter
    def poll_interval(self, value):
        self._poll_interval = value
        self._update_poll(self._last_poll)

    @property
    def auth(self):
        """
        :return:            return my own auth or the parent one if available ...
        """
        if self._auth is None:
            if not isinstance(self.parent, FakeJenkinsBase):
                self._auth = self.parent.auth
        if self._auth is None:
            self._auth = jenkinsapi.requester.JenkinsAuth()
        return self._auth

    @auth.setter
    def auth(self, value):
        assert isinstance(value, (jenkinsapi.requester.JenkinsAuth, None)),\
            'Auth must be an instance of JenkinsAuth and not %s' % value.__class__.__name__
        self._auth = value
        # we have to invalidate requester
        self._requester = None

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout
        # we have to invalidate requester
        self._requester = None


    @property
    def api(self):
        """
        Could be perhaps done more efficiently ...
        :return:    Jenkins API URL
        """
        if self._api is None:
            self._api = jenkinsapi.misc.normalize_url(jenkinsapi.misc.join_url(self._url, self._API))
        return self._api

    def __lt__(self, other):
        """
        Just comparing last poll timestamp
        """
        assert isinstance(other, JenkinsBase), 'I can compare only instances of %s' % self.__class__.__name__
        return self._last_poll < other._last_poll

    def __gt__(self, other):
        """
        Just comparing last poll timestamp
        """
        assert isinstance(other, JenkinsBase), 'I can compare only instances of %s' % self.__class__.__name__
        return self._last_poll > other._last_poll

    def __eq__(self, other):
        """
        True only if this is the same instance of the object
        """
        assert isinstance(other, JenkinsBase), 'I can compare only instances of %s' % self.__class__.__name__
        return id(self) == id(other)

    def __ne__(self, other):
        """
        True only if this is the same instance of the object
        """
        assert isinstance(other, JenkinsBase), 'I can compare only instances of %s' % self.__class__.__name__
        return id(self) != id(other)

    def __repr__(self):
        return '<%s at 0x%x>' % (self.url, id(self))

    @property
    def last_poll(self):
        return self._last_poll

    @property
    def data(self):
        self.auto_poll()
        return self._data

    # expose data as dictionary

    def __len__(self):
        self.auto_poll()
        return self._data.__len__()

    def __getitem__(self, item):
        self.auto_poll()
        return self._data.__getitem__(item)

    def __setitem__(self, key, value):
        return self._data.__setitem__(key, value)

    def __delitem__(self, key):
        return self._data.__delitem__(key)

    def __iter__(self):
        self.auto_poll()
        return self._data.__iter__()

    def __contains__(self, item):
        self.auto_poll()
        return self._data.__contains__(item)

    def get(self, key, default=None):
        self.auto_poll()
        return self._data.get(key, default)
