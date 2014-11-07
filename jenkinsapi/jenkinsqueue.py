from jenkinsapi.jenkins import Jenkins
from jenkinsapi.jenkinsbase import JenkinsBase
from jenkinsapi.misc import normalize_url, RefQueue, join_url, default
from jenkinsapi.requester import JenkinsAuth

__author__ = 'sedlacek'


class JenkinsQueue(JenkinsBase):

    _QUEUE = 'queue'

    def __init__(self, refobj=None, url=None, poll_interval=None, auth=JenkinsAuth(), timeout=None):
        """
        :param refobj:            instance RefQueue
        :param url:                 or full job url
        :param poll_interval:       api poll interval
        :param auth:                authentication object
        """
        assert (refobj is not None and url is None) or (refobj is None and url is not None), 'The only one from {refqueue, url} can be used.'
        if url is not None:
            url = normalize_url(url)
            # we have to create a jenkins object
            jenkinsurl = normalize_url(url[:-1 - len(self._QUEUE)])
            self._jenkins = Jenkins(url=jenkinsurl, poll_interval=poll_interval, auth=auth, timeout=timeout)
        else:
            assert isinstance(refobj, RefQueue)
            self._jenkins = refobj.jenkins
            url = normalize_url(join_url(self._jenkins.url, self._QUEUE))

        super(JenkinsQueue, self).__init__(url=url,
                                           auth=default(auth, self._jenkins.auth),
                                           poll_interval=default(poll_interval, self._jenkins.poll_interval),
                                           timeout=default(timeout, self._jenkins._timeout))