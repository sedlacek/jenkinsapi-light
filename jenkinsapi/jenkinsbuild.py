from jenkinsapi.jenkinsbase import JenkinsBase
from jenkinsapi.jenkinsjob import JenkinsJob
from jenkinsapi.misc import normalize_url, RefBuild, join_url, default
from jenkinsapi.requester import JenkinsAuth

__author__ = 'sedlacek'


class JenkinsBuild(JenkinsBase):

    def __init__(self, refobj=None, url=None, poll_interval=None, auth=JenkinsAuth(), timeout=None):
        """
        :param refobj:            instance RefBuild
        :param url:                 or full job url
        :param poll_interval:       api poll interval
        :param auth:                authentication object
        """
        assert (refobj is not None and url is None) or (refobj is None and url is not None), 'The only one from {refbuil, url} can be used.'
        if url is not None:
            url = normalize_url(url)
            self._number = url.split('/')[-1]
            # we have to create a jenkins job object
            self._job = JenkinsJob(url=normalize_url(url[:-len(self._number)]), poll_interval=poll_interval,
                                   auth=auth, timeout=timeout)
        else:
            assert isinstance(refobj, RefBuild)
            self._job = refobj.job
            self._number = refobj.number
            url = normalize_url(join_url(self._job.url, self._number))
        super(JenkinsBuild, self).__init__(url=url,
                                           auth=default(auth, self._job.auth),
                                           poll_interval=default(poll_interval, self._job.poll_interval),
                                           timeout=default(timeout, self._job._timeout))
        self._console_more_data = True
        self._console_text_size = 0

    @property
    def job(self):
        return self._job

    @property
    def number(self):
        return int(self._number)

    @property
    def ok(self):
        try:
            return self['result'] == 'SUCCESS'
        except KeyError:
            return None

    @property
    def failed(self):
        try:
            return self['result'] == 'FAILURE'
        except KeyError:
            return None

    @property
    def aborted(self):
        try:
            return self['result'] == 'ABORTED'
        except KeyError:
            return None

    def poll_console(self, reset=False):
        """
        Return not yet seen console output or None if there is nothing more to return
        return list of strings (split by \n)

        :param reset:       reset counters and starts polling console from the first line
        """
        if reset:
            self._console_text_size = 0
            self._console_more_data = True

        if not self._console_more_data:
            return None

        url = '%s/logText/progressiveText' % self.url
        request = self.requester.post(url=url, data={'start': self._console_text_size})


        try:
            self._console_more_data = request.headers['x-more-data'] == 'true'
        except KeyError:
            self._console_more_data = False
        # noinspection PyBroadException
        try:
            newsize = int(request.headers['x-text-size'])
            # we did not receive eny update ...
            if self._console_text_size == newsize:
                return None
            self._console_text_size = int(request.headers['x-text-size'])
        except:
            pass
        return request.content.splitlines()