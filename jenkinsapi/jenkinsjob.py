import json
import jenkinsapi.jenkinsbase
import jenkinsapi.requester
import jenkinsapi.jenkins
import jenkinsapi.misc
import jenkinsapi.jenkinsqueueitem
import jenkinsapi.jenkinsbuild

__author__ = 'sedlacek'

class _JenkinsJobMeta(type):
    """
    Lets make sure that when parent is jenkins, any job is properly registered there

    We prevent creation of another instance of JenkinsJob object,
    if it already exist and we just update existing instance
    """
    def __call__(cls, parent=None, objid=None, url=None, data=None, poll_interval=None,
                 auth=None, timeout=None):
        assert (objid is None and url is not None) or (objid is not None and url is None), \
            'Either url or objid can be defined, but not both!'
        if isinstance(parent, jenkinsapi.jenkins.Jenkins):
            # ok parent is instance of Jenkins
            try:
                res = parent._jobs[objid if objid is not None else JenkinsJob.objid_from_url(url)]
                res.__an_update__(poll_interval=poll_interval, auth=auth, timeout=timeout)
                return res
            except KeyError:
                pass
        return super(_JenkinsJobMeta, cls).__call__(parent=parent, objid=objid, url=url, data=data,
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
        self._builds = {}
        self._firstbuild = None
        super(JenkinsJob, self).__init__(parent=parent,
                                         objid=objid,
                                         url=url,
                                         data=data,
                                         poll_interval=poll_interval,
                                         auth=auth,
                                         timeout=timeout)
        if isinstance(self.parent, jenkinsapi.jenkins.Jenkins):
            self.parent.update_job_ref(self)

    @property
    def name(self):
        return self.objid

    @property
    def builds(self):
        return self._builds

    def update_build_ref(self, otherbuild):
        """
        Updating build reference

        :param otherbuild:      JenkinsBuild instance
        :return:                updated queue item
        """
        try:
            mybuild = self._builds[otherbuild.objid]

            # we want to compare objects only if they are not the same
            if mybuild != otherbuild and mybuild < otherbuild:
                mybuild.__an_update__(auth=otherbuild.auth, poll_interval=otherbuild.poll_interval,
                                      timeout=otherbuild.timeout)
                # now merge the data
                mybuild.poll(data=otherbuild.data, now=otherbuild.last_poll)
        except KeyError:
            self._builds[otherbuild.objid] = otherbuild

        return self._builds[otherbuild.objid]

    def delete_build_ref(self, build):
        """
        Delete queueitem reference

        :param build:        Either JenkinsBuild or objid
        :return:             self
        """
        if isinstance(build, jenkinsapi.jenkinsbuild.JenkinsBuild):
            buildid = build.objid
        else:
            buildid = build

        # delete from job list
        del self._builds[buildid]
        return self

    def _update_data(self, data, now=None):
        super(JenkinsJob, self)._update_data(data=data, now=now)

        for build in self._data['builds']:
            self.update_build_ref(jenkinsapi.jenkinsbuild.JenkinsBuild(parent=self,
                                                                       url=build['url'],
                                                                       poll_interval=self.poll_interval,
                                                                       auth=self.auth,
                                                                       timeout=self.timeout))
        with jenkinsapi.misc.IgnoreKeyError():
            if self._data['firstBuild'] is None:
                self._firstbuild = None
            else:
                self._firstbuild = jenkinsapi.jenkinsbuild.JenkinsBuild(parent=self,
                                                                        url=self._data['firstBuild'],
                                                                        poll_interval=self.poll_interval,
                                                                        auth=self.auth,
                                                                        timeout=self.timeout)

    def enqueue_build(self, cause=None, params=None, files=None):
        """
        Schedule a build with params
        :param cause:       build cause
        :param params:      non file build parameters
        :param files:       file build paramenters
        :return:            queue item
        """
        # we ignore files for now ...
        build_params = jenkinsapi.misc.merge_all_dict(
            {'cause': cause} if cause is not None else None,
            params
            )

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

