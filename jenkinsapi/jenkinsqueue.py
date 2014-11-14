import jenkinsapi.jenkinsbase
import jenkinsapi.jenkinsqueueitem
import jenkinsapi.requester
import jenkinsapi.jenkins

__author__ = 'sedlacek'

class _JenkinsQueueMeta(type):
    """
    Lets make sure that when parent is jenkins, We use the queue from jenkins object

    """
    def __call__(cls, parent=None, objid=None, url=None, data=None, poll_interval=None,
                 auth=None, timeout=None):
        if auth is None:
            auth = jenkinsapi.requester.JenkinsAuth()
        assert (objid is None and url is not None) or (objid is not None and url is None), \
            'Either url or objid can be defined, but not both!'
        if isinstance(parent, jenkinsapi.jenkins.Jenkins):
            # ok parent is instance of Jenkins
            try:
                res = parent.queue
                res.__an_update__(poll_interval=poll_interval, auth=auth, timeout=timeout)
                return res
            except AttributeError:
                pass
        return super(_JenkinsQueueMeta, cls).__call__(parent=parent, objid=objid, data=data,
                                                            poll_interval=poll_interval, auth=auth, timeout=timeout)

class JenkinsQueue(jenkinsapi.jenkinsbase.JenkinsBase):
    """
    Representation of jenkins queue (There is only one queue for all jobs)
    """

    __metaclass__ = _JenkinsQueueMeta

    def __init__(self, parent=None, objid=None, url=None, data=None, poll_interval=None,
                 auth=jenkinsapi.requester.JenkinsAuth(), timeout=None):
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
        self._data = {}
        super(JenkinsQueue, self).__init__(parent=parent,
                                           objid=objid,
                                           url=url,
                                           data=data,
                                           poll_interval=poll_interval,
                                           auth=auth,
                                           timeout=timeout)
        self._jenkins = self.parent
        self._items = {}


    @property
    def items(self):
        return self._items

    def _update_data(self, data, now=None):
        """
        We would like to have in the queue real queue items ...
        :param now:
        """
        # store all the item keys
        keystoremove = self.items.keys()
        for item in data['items']:
            if item['id'] in self.items:
                self.items[item['id']].poll(data=item, now=now)
                keystoremove.remove(item['id'])
            else:
                jenkinsapi.jenkinsqueueitem.JenkinsQueueItem(parent=self.parent,  objid=item['id'], data=item,
                                                             poll_interval=self.poll_interval,
                                                             auth=self.auth, timeout=self.timeout)
        # and now delete all queue items which are no longer in jenkins queue
        for key in keystoremove:
            self._delete_queueitem_ref(key)

    def __setitem__(self, key, value):
        if not isinstance(value, jenkinsapi.jenkinsqueueitem.JenkinsQueueItem):
            raise ValueError('Expecting %s and got %s' % ('JenkinsQueueItem', value.__class__.__name__))
        return super(JenkinsQueue, self).__setitem__(key, value)

    def _update_queueitem_ref(self, otheritem):
        """
        Updating job reference

        :param queueitem:       JenkinsQueueItem instance
        :return:                updated queue item
        """
        try:
            myitem = self.items[otheritem.item]

            # we want to compare objects only if they are not the same
            if myitem != otheritem and myitem < otheritem:
                myitem.__an_update__(auth=otheritem.auth, poll_interval=otheritem.poll_interval,
                                   timeout=otheritem.timeout)
                # now merge the data
                myitem.poll(data=otheritem.data, now=otheritem.last_poll)
        except KeyError:
            self.items[otheritem.item] = otheritem

        return self.items[otheritem.item]

    def _delete_queueitem_ref(self, item):
        """
        Delete queueitem reference

        :param item:         Either JenkinsJob or objid
        :return:             self
        """
        if isinstance(item, jenkinsapi.jenkinsqueueitem.JenkinsQueueItem):
            itemid = item.objid
        else:
            itemid = item

        # delete from job list
        del self.items[itemid]
        return self

