from jenkinsapi.jenkinsbase import JenkinsBase
from jenkinsapi.jenkinsqueue import JenkinsQueue
from jenkinsapi.misc import normalize_url, RefQueueItem, join_url, default
from jenkinsapi.requester import JenkinsAuth

__author__ = 'sedlacek'


class JenkinsQueueItem(JenkinsBase):
    """
    Queue item (queue is in jenkins scope
    """

    _QUEUEITEM = 'item'

    def __init__(self, refobj=None, url=None, poll_interval=None, auth=JenkinsAuth(), timeout=None):
        """
        :param refobj:        instance RefQueueItem
        :param url:                 or full queue item url
        :param poll_interval:       api poll interval
        :param auth:                authentication object
        """
        assert (refobj is not None and url is None) or (refobj is None and url is not None), 'The only one from {refqueueitem,, url} can be used.'
        if url is not None:
            url = normalize_url(url)
            self._itemid = url.split('/')[-1]
            # we have to create a jenkins job object
            self._queue = JenkinsQueue(url=normalize_url(url[:-1 - len(self._itemid) - len(self._QUEUEITEM)]),
                                       poll_interval=poll_interval, auth=auth, timeout=timeout)
        else:
            assert isinstance(refobj, RefQueueItem)
            self._queue = refobj.queue
            self._itemid = refobj.itemid
            url = normalize_url(join_url(self._queue.url, self._QUEUEITEM, self._itemid))

        super(JenkinsQueueItem, self).__init__(url=url, auth=default(auth, self._queue.auth),
                                               poll_interval=default(poll_interval, self._queue.poll_interval),
                                               timeout=default(timeout, self._queue._timeout))