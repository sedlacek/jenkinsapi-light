import jenkinsapi.jenkinsbase
import jenkinsapi.jenkins
import jenkinsapi.requester
import jenkinsapi.jenkinsqueue
import jenkinsapi.jenkinsjob
import jenkinsapi.jenkinsbuild
import jenkinsapi.misc
from time import sleep

__author__ = 'sedlacek'

class _JenkinsQueueItemMeta(type):
    """
    Lets make sure that when parent is jenkins, We use the queue from jenkins object

    """
    def __call__(cls, parent=None, objid=None, url=None, data=None, poll_interval=None,
                 auth=None, timeout=None):
        assert (objid is None and url is not None) or (objid is not None and url is None), \
            'Either url or objid can be defined, but not both!'
        if isinstance(parent, jenkinsapi.jenkins.Jenkins):
            myqueue = parent.queue
        elif isinstance(parent, jenkinsapi.jenkinsqueue.JenkinsQueue):
            myqueue = parent
        elif isinstance(parent, jenkinsapi.jenkinsjob.JenkinsJob) and isinstance(parent.jenkins, jenkinsapi.jenkins.Jenkins):
            myqueue = parent.jenkins.queueu
        else:
            myqueue = None

        if myqueue is not None:
            # ok parent is instance of Jenkins
            try:
                res = myqueue._items[objid if objid is not None else JenkinsQueueItem.objid_from_url(url)]
                res.__an_update__(poll_interval=poll_interval, auth=auth, timeout=timeout)
                return res
            except KeyError:
                pass
        return super(_JenkinsQueueItemMeta, cls).__call__(parent=myqueue, objid=objid, url=url, data=data,
                                                            poll_interval=poll_interval, auth=auth, timeout=timeout)

class JenkinsQueueItem(jenkinsapi.jenkinsbase.JenkinsBase):
    """
    Queue item (queue is in jenkins scope
    """

    __metaclass__ = _JenkinsQueueItemMeta

    _EXTRA = 'queue/item'

    def __init__(self, parent=None, objid=None, url=None, data=None, poll_interval=None, auth=jenkinsapi.requester.JenkinsAuth(), timeout=None):
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
        self._build = None
        self._job = None
        super(JenkinsQueueItem, self).__init__(parent=parent,
                                               objid=objid,
                                               url=url,
                                               data=data,
                                               poll_interval=poll_interval,
                                               auth=auth,
                                               timeout=timeout)
        self._queue = self.parent
        if isinstance(self.queue, jenkinsapi.jenkinsqueue.JenkinsQueue):
            self.queue.update_queueitem_ref(self)
        self._item = self.objid

    @property
    def item(self):
        return self._item

    @property
    def queue(self):
        return self._queue

    @property
    def job(self):
        return self._job

    @property
    def build(self):
        if self._build is None:
            self.auto_poll()
        return self._build

    def _update_data(self, data, now=None):
        super(JenkinsQueueItem, self)._update_data(data, now)
        if self._job is None:
            with jenkinsapi.misc.IgnoreKeyError():
                if self._data['task'] is not None:
                    self._job = jenkinsapi.jenkinsjob.JenkinsJob(parent=self.jenkins,
                                                                 url=data['task']['url'],
                                                                 poll_interval=self._poll_interval,
                                                                 auth=self._auth,
                                                                 timeout=self._timeout)
        if self._build is None:
            with jenkinsapi.misc.IgnoreKeyError():
                if self._data['executable'] is not None:
                    self._build = jenkinsapi.jenkinsbuild.JenkinsBuild(parent=self._job,
                                                                       url=data['executable']['url'],
                                                                       poll_interval=self._poll_interval,
                                                                       auth=self._auth,
                                                                       timeout=self._timeout)
    @property
    def cancelled(self):
        self.auto_poll()
        with jenkinsapi.misc.IgnoreKeyError():
            if self._data['cancelled']:
                return True
        return False

    @property
    def dequeued(self):
        self.auto_poll()
        with jenkinsapi.misc.IgnoreKeyError():
            if self._data['executable'] is not None:
                return True
        return False

    @property
    def inqueue(self):
        return not self.cancelled and not self.dequeued

    def block(self, poll_interval=None):
        """
        :param poll_interval:       poll interval, default 1 second
        :return:                    self
        """
        if poll_interval is None:
            if self.poll_interval is not None and self.poll_interval > 0:
                poll_interval = self.poll_interval
            else:
                # set default
                poll_interval = jenkinsapi.misc.DEFAULT_POLL_INTERVAL
        assert poll_interval >= 1, 'Insanely short poll_interval (%f)' % poll_interval
        while self.poll().inqueue:
            sleep(poll_interval)
        return self
