import json
import jenkinsapi.jenkinsbase
import jenkinsapi.requester
import jenkinsapi.jenkins
import jenkinsapi.misc
import jenkinsapi.jenkinsqueueitem

__author__ = 'sedlacek'

class _JenkinsJobMeta(type):
    """
    Lets make sure that when parent is jenkins, any job is properly registered there

    We prevent creation of another instance of JenkinsJob object,
    if it already exist and we just update existing instance
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
                res = parent.jobs[objid if objid is not None else JenkinsJob.objid_from_url(url)]
                res.__an_update__(poll_interval=poll_interval, auth=auth, timeout=timeout)
                return res
            except KeyError:
                pass
        return super(_JenkinsJobMeta, cls).__call__(parent=parent, objid=objid, data=data,
                                                            poll_interval=poll_interval, auth=auth, timeout=timeout)


class JenkinsJob(jenkinsapi.jenkinsbase.JenkinsBase):

    __metaclass__ = _JenkinsJobMeta
    _EXTRA = 'job'

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
        super(JenkinsJob, self).__init__(parent=parent,
                                         objid=objid,
                                         url=url,
                                         data=data,
                                         poll_interval=poll_interval,
                                         auth=auth,
                                         timeout=timeout)
        self._jenkins = self.parent
        self._name = self.objid

        if isinstance(self.parent, jenkinsapi.jenkins.Jenkins):
            self.parent._update_job_ref(self)

    @property
    def jenkins(self):
        return self._jenkins

    @property
    def name(self):
        return self._name

    def enqueue_build(self, cause=None, params=None, files=None):
        """
        Schedule a build with params
        :param cause:       build cause
        :param params:      non file build parameters
        :param files:       file build paramenters
        :return:            queue item
        """
        build_params = {}
        if cause is not None:
            build_params['cause'] = cause
        # mangle build params for jenkins
        bp = []
        if params is not None:
            for param, value in params.iteritems():
                bp.append({'name': param, 'value': value})
        if files is not None:
            for file_ in files:
                bp.append({'name': file_, 'file': file_})
        build_params['json'] = json.dumps({'parameter': bp})

        xxxx = """
            if params is None or files is not None:
                url = '%s/build' % self.url
            else:
                url = '%s/buildWithParameters' % self.url
            """

        url = '%s/buildWithParameters' % self.url

        # now we are ready to try enqueue a build
        response = self.requester.post(url=url, data=build_params, files=files)

        if response.status_code not in (200, 201):
            raise jenkinsapi.misc.JenkinsApiRequestFailed('Request (%s) failed %d %s for %s'
                                                          % ('POST', response.status_code, response.reason,
                                                             response.url))

        return jenkinsapi.jenkinsqueueitem.JenkinsQueueItem(parent=self.parent, url=response.headers['location'],
                                                            auth=self.auth, timeout=self.timeout,
                                                            poll_interval=self.poll_interval)

