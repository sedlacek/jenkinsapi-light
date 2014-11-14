import jenkinsapi.jenkinsbase
import jenkinsapi.requester
import jenkinsapi.jenkins

__author__ = 'sedlacek'


class JenkinsView(jenkinsapi.jenkinsbase.JenkinsBase):

    _EXTRA = 'view'

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
        super(JenkinsView, self).__init__(parent=parent,
                                          objid=objid,
                                          url=url,
                                          data=data,
                                          poll_interval=poll_interval,
                                          auth=auth,
                                          timeout=timeout)
        self._jenkins = self.parent
        self._name = self.objid

        if isinstance(self.parent, jenkinsapi.jenkins.Jenkins):
            self.parent.view[self.name] = self


    @property
    def jenkins(self):
        return self._jenkins

    @property
    def name(self):
        return self._name

