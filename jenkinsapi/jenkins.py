import jenkinsapi.jenkinsbase
import jenkinsapi.jenkinsqueue
import jenkinsapi.requester
import jenkinsapi.jenkinsjob

__author__ = 'sedlacek'


class Jenkins(jenkinsapi.jenkinsbase.JenkinsBase):
    """
    Jenkins is to object in the jenkins API, obviously it does not have any parent neither any objid

    It is as well container for keeping all the objects only once
    """

    def __init__(self, url=None, data=None, poll_interval=None, auth=jenkinsapi.requester.JenkinsAuth(), timeout=None):
        """
        :param parent:              parent object
        :param objid:               object id (name)
        :param data:                we already got the data, so initiate the object with the data
        :param url:                 or full job url
        :param poll_interval:       api poll interval
        :param auth:                authentication object
        """
        super(Jenkins, self).__init__(url=url,
                                      data=data,
                                      poll_interval=poll_interval,
                                      auth=auth,
                                      timeout=timeout)
        # JenkinsBase.__init__ class guessed parent and objid, so lets correct it
        self._parent = None
        self.objid = None
        self._queue = jenkinsapi.jenkinsqueue.JenkinsQueue(parent=self, objid='queue', timeout=timeout,
                                                           poll_interval=poll_interval, auth=auth)
        self._jobs = {}
        self._views = {}


    @property
    def parent(self):
        return None

    @property
    def queue(self):
        return self._queue

    @property
    def jobs(self):
        self.auto_poll()
        return self._jobs

    @property
    def views(self):
        return self._views

    def update_job_ref(self, otherjob):
        """
        Updating job reference

        :param otherjob:        JenkinsJob instance
        :return:                updated job
        """
        try:
            myjob = self._jobs[otherjob.objid]

            # we want to compare objects only if they are not the same
            if myjob != otherjob and myjob < otherjob:
                myjob.__an_update__(auth=otherjob.auth, poll_interval=otherjob.poll_interval, timeout=otherjob.timeout)
                # now merge the data
                myjob.poll(data=otherjob.data, now=otherjob.last_poll)
        except KeyError:
            self._jobs[otherjob.objid] = otherjob

        return self._jobs[otherjob.objid]

    def delete_job_ref(self, job):
        """
        Delete job reference

        :param job:         Either JenkinsJob or objid
        :return:            self
        """
        if isinstance(job, jenkinsapi.jenkinsjob.JenkinsJob):
            jobid = job.objid
        else:
            jobid = job

        # delete from job list
        try:
            del self._jobs[jobid]
        except KeyError:
            # something else might have deleted it already
            pass
        return self

    def _update_data(self, data, now=None):
        """
        We need to create job structure and as well view structure
        :param now:
        """
        self._data = data
        # store all the item keys
        keystoremove = self._jobs.keys()
        for job in data['jobs']:
            if job['name'] in keystoremove:
                # we do not want to remove this one
                keystoremove.remove(job['name'])
            else:
                jenkinsapi.jenkinsjob.JenkinsJob(parent=self, objid=job['name'], poll_interval=self.poll_interval,
                                                 auth=self.auth, timeout=self.timeout)
        # and now delete all jobs which are no longer in jenkins
        for key in keystoremove:
            self.delete_job_ref(key)
