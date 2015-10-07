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
        assert (parent is None and url is not None) or (url is None and parent is not None), \
            'Either queue url or a parent can be defined, but not both!'
        if parent is None:
            # ok return queue based on url
            return super(_JenkinsQueueMeta, cls).__call__(parent=parent, objid=objid, url=url, data=data,
                                                          poll_interval=poll_interval, auth=auth, timeout=timeout)
        else:
            if isinstance(parent, jenkinsapi.jenkins.Jenkins):
                # ok parent is instance of Jenkins, queue is attached to jenkins root object
                jenkins = parent.jenkins
                try:
                    res = jenkins.queue
                    res.__an_update__(poll_interval=poll_interval, auth=auth, timeout=timeout)
                    return res
                except AttributeError:
                    # if we are here, we are sdesperate, so lets try to create new queue object
                    return super(_JenkinsQueueMeta, cls).__call__(parent=jenkins, objid='queue', url=url, data=data,
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
        self._items = {}
        super(JenkinsQueue, self).__init__(parent=parent,
                                           objid=objid,
                                           url=url,
                                           data=data,
                                           poll_interval=poll_interval,
                                           auth=auth,
                                           timeout=timeout)


    @property
    def items(self):
        self.auto_poll()
        return self._items

    def _update_data(self, data, now=None):
        """
        We would like to have in the queue real queue items ...
        :param now:
        """
        # store all the item keys
        keystoremove = self._items.keys()
        for item in data['items']:
            itemid = str(item['id'])
            if itemid in self._items:
                self._items[itemid].poll(data=item, now=now)
                keystoremove.remove(itemid)
            else:
                jenkinsapi.jenkinsqueueitem.JenkinsQueueItem(parent=self.parent,  objid=itemid, data=item,
                                                             poll_interval=self.poll_interval,
                                                             auth=self.auth, timeout=self.timeout)
        # and now delete all queue items which are no longer in jenkins queue
        for key in keystoremove:
            self.delete_queueitem_ref(key)


    def update_queueitem_ref(self, otheritem):
        """
        Updating job reference

        :param queueitem:       JenkinsQueueItem instance
        :return:                updated queue item
        """
        try:
            myitem = self._items[otheritem.objid]

            # we want to compare objects only if they are not the same
            if myitem != otheritem and myitem < otheritem:
                myitem.__an_update__(auth=otheritem.auth, poll_interval=otheritem.poll_interval,
                                   timeout=otheritem.timeout)
                # now merge the data
                myitem.poll(data=otheritem.data, now=otheritem.last_poll)
        except KeyError:
            self._items[otheritem.objid] = otheritem

        return self._items[otheritem.objid]

    def delete_queueitem_ref(self, item):
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
        del self._items[itemid]
        return self

