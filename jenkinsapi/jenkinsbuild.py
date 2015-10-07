import jenkinsapi.jenkinsbase
import jenkinsapi.jenkinsjob
import jenkinsapi.misc
import jenkinsapi.requester
import jenkinsapi.jenkinsartifacts

from time import sleep

__author__ = 'sedlacek'

class _JenkinsBuild(type):
    """
    Lets make sure that when parent is jenkins, We use the queue from jenkins object

    """
    def __call__(cls, parent=None, objid=None, url=None, data=None, poll_interval=None,
                 auth=None, timeout=None):
        assert (objid is None and url is not None) or (objid is not None and url is None), \
            'Either url or objid can be defined, but not both!'
        myjob = parent

        if myjob is not None:
            # ok parent is instance of Jenkins
            try:
                res = myjob.builds[objid if objid is not None else JenkinsBuild.objid_from_url(url)]
                res.__an_update__(poll_interval=poll_interval, auth=auth, timeout=timeout)
                return res
            except KeyError:
                pass
        return super(_JenkinsBuild, cls).__call__(parent=parent, objid=objid, url=url, data=data,
                                                            poll_interval=poll_interval, auth=auth, timeout=timeout)


class JenkinsBuild(jenkinsapi.jenkinsbase.JenkinsBase):

    __metaclass__ = _JenkinsBuild

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
        :param poll_interval:       0 - data polled al  ways when value requested
                                    >0 - interval in which data are refreshed (in seconds)
                                    None - data automatically polled only once, when data are accessed
        """
        self._console_text_size = 0
        self._console_more_data = True

        super(JenkinsBuild, self).__init__(parent=parent,
                                           objid=objid,
                                           url=url,
                                           data=data,
                                           poll_interval=poll_interval,
                                           auth=auth,
                                           timeout=timeout)

        if isinstance(self.job, jenkinsapi.jenkinsjob.JenkinsJob):
            self.job.update_build_ref(self)

    @property
    def job(self):
        if hasattr(self, '_job'):
            return self._job
        if isinstance(self.parent, jenkinsapi.jenkinsjob.JenkinsJob):
            self._job = self.parent
        else:
            self._job = None
        return self._job

    @property
    def number(self):
        return int(self.objid)

    @property
    def ok(self):
        self.auto_poll()
        try:
            return self['result'] == 'SUCCESS'
        except KeyError:
            raise jenkinsapi.misc.JenkinsNotAvailable('Cannot yet retrieve build status.')

    @property
    def failed(self):
        self.auto_poll()
        try:
            return self['result'] == 'FAILURE'
        except KeyError:
            raise jenkinsapi.misc.JenkinsNotAvailable('Cannot yet retrieve build status.')

    @property
    def aborted(self):
        self.auto_poll()
        try:
            return self['result'] == 'ABORTED'
        except KeyError:
            raise jenkinsapi.misc.JenkinsNotAvailable('Cannot yet retrieve build status.')

    @property
    def isbuilding(self):
        self.auto_poll()
        return self['building']

    @property
    def artifacts(self):
        self.auto_poll()
        if not hasattr(self, '_artifacts') and 'artifacts' in self._data:
            self._artifacts = jenkinsapi.jenkinsartifacts.JenkinsArtifacts(parent=self, data=self._data['artifacts'])
        return self._artifacts


    def console(self, poll_interval=1, reset=False):
        """
        yield next console line, or None (if polling is off)
        or raise jenkinsapi.misc.JenkinsNoMoreConsoleData if we already read all the lines


        :type poll_interval:        0 or None, means no polling, >0 means polling in seconds
                                    default is 1 second
        :param reset:               reset counters and starts polling console from the first line
        """
        if reset:
            self._console_text_size = 0
            self._console_more_data = True

        if not self._console_more_data:
            # well, we are behind the end
            raise jenkinsapi.misc.JenkinsNoMoreConsoleData

        url = '%s/logText/progressiveText' % self.url

        while True:
            #Iterate trough console, console data
            request = self.requester.post(url=url, data={'start': self._console_text_size})

            try:
                # Should we expect more lines?
                self._console_more_data = request.headers['x-more-data'] == 'true'
            except KeyError:
                self._console_more_data = False
            # noinspection PyBroadException
            try:
                newsize = int(request.headers['x-text-size'])
                # we did not receive eny update ...
                if self._console_text_size == newsize:
                    if poll_interval is None or poll_interval == 0:
                        # well we do not want to do polling here, so yield None
                        yield None
                    else:
                        # lets wait and poll again
                        sleep(poll_interval)
                        continue
                self._console_text_size = newsize
            except Exception as e:
                # broken console protocol, lets raise an exception here
                raise ValueError('Cannot get console text size :(%s)' % str(e))
            for line in request.content.splitlines():
                yield line
            if not self._console_more_data:
                # nothing more to process...
                break

    def block(self, poll_interval):
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
        while self.poll().isbuilding:
            sleep(poll_interval)
        return self