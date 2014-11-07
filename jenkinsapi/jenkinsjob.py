import json
from jenkinsapi.jenkins import Jenkins
from jenkinsapi.jenkinsbase import JenkinsBase
from jenkinsapi.misc import normalize_url, RefJob, join_url, default, JenkinsApiRequestFailed
from jenkinsapi.requester import JenkinsAuth

__author__ = 'sedlacek'


class JenkinsJob(JenkinsBase):

    _JOB = 'job'

    def __init__(self, refobj=None, url=None, poll_interval=None, auth=JenkinsAuth(), timeout=None):
        """
        :param refobj:              instance RefJob
        :param url:                 or full job url
        :param poll_interval:       api poll interval
        :param auth:                authentication object
        """
        assert (refobj is not None and url is None) or (refobj is None and url is not None), 'The only one from {refjob, url} can be used.'
        if url is not None:
            url = normalize_url(url)
            self._name = url.split('/')[-1]
            # we have to create a jenkins object
            jenkinsurl = normalize_url(url[:-1 - len(self._name) - len(self._JOB)])
            self._jenkins = Jenkins(url=jenkinsurl, poll_interval=poll_interval, auth=auth, timeout=timeout)
        else:
            assert isinstance(refobj, RefJob)
            self._jenkins = refobj.jenkins
            self._name = refobj.name
            url = normalize_url(join_url(self._jenkins.url, self._JOB, self._name))

        super(JenkinsJob, self).__init__(url=url,
                                         auth=default(auth, self._jenkins.auth),
                                         poll_interval=default(poll_interval, self._jenkins.poll_interval),
                                         timeout=default(timeout, self._jenkins._timeout))

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
        build_params={}
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

        """
        if params is None or files is not None:
            url = '%s/build' % self.url
        else:
            url = '%s/buildWithParameters' % self.url
        """

        url = '%s/buildWithParameters' % self.url

        # now we are ready to try enqueue a build
        response = self.requester.post(url=url, data=build_params, files=files)

        if response.status_code not in (200, 201):
            raise JenkinsApiRequestFailed('Request (%s) failed %d %s for %s' % ('POST', response.status_code, response.reason, response.url))

        print response.headers['location']

        print 'Response:', response