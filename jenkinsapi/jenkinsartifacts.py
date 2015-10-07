import jenkinsapi.jenkinsbase
import jenkinsapi.jenkinsbuild
import jenkinsapi.requester
import jenkinsapi.misc
import os

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)

__author__ = 'sedlacek'


class Artifact(object):
    """
    Build artifacts
    """
    def __init__(self, displaypath, filename, relativepath, parent):
        """
        Artifact object, allowing retrieval of the artifact, using jenkins authorization primitives
        :param displaypath:         artifact display path
        :param filename:            artifact filename
        :param relativepath:        artifact relative path
        :param parent:              a parent jenkinsapi object (must be jenkinsapi.jenkinsartifacts.JenkinsArtifacts)
        :param file tofile:         a open file ...
        """
        self.displaypath = displaypath
        self.filename = filename
        self.relativepath = relativepath
        assert isinstance(parent, JenkinsArtifacts), \
            'Artifact parent must be jenkinsapi.jenkinsartifacts.JenkinsArtifacts!'
        self.parent = parent
        self._requester = None
        self._url = jenkinsapi.misc.normalize_url(jenkinsapi.misc.join_url(self.parent.parent.url, 'artifact', self.relativepath))

    @property
    def url(self):
        return self._url

    @property
    def requester(self):
        if self._requester is None:
            if self.parent.auth.token is not None:
                params = {'token': self.parent.auth.token}
            else:
                params = {}
            self._requester = jenkinsapi.requester.Requester(
                url=self.parent.url,
                params=params,
                username=self.parent.auth.auth.username,
                password=self.parent.auth.auth.password,
                timeout=self.parent.timeout,
            )
        return self._requester

    def get(self):
        return self._requester.get(url=self.url).content

    def iterget(self, blocksize):
        """
        Download artifact write directly to open to_file
        :param to_file:     an open file
        """
        return self.requester.iterget(url=self.url, blocksize=blocksize)

    def write(self, fullpath):
        """
        save artifact to full path
        """
        with open(fullpath, 'wb') as w:
            for block in self.iterget(blocksize=8192):
                w.write(block)
        return self


class _JenkinsArtifacts(type):
    """
    Lets make sure that when parent is jenkins, We use the queue from jenkins object

    """
    def __call__(cls, parent=None, objid=None, url=None, data=None, poll_interval=None,
                 auth=None, timeout=None):
        objectid = 'artifacts'
        assert (parent is None and url is not None) or (parent is not None and url is None), \
            'Either url or parent can be defined, but not both!'
        mybuild = parent

        if mybuild is not None:
            assert isinstance(mybuild, jenkinsapi.jenkinsbuild.JenkinsBuild),\
                'Artifacts parent must be JenkinsBuild instance!'

        return super(_JenkinsArtifacts, cls).__call__(parent=parent, objid=objid, url=url, data=data,
                                                            poll_interval=poll_interval, auth=auth, timeout=timeout)


class JenkinsArtifacts(jenkinsapi.jenkinsbase.JenkinsBase):
    """
    Override method deriving parent and id from URL
    """

    __metaclass__ = _JenkinsArtifacts

    def __init__(self, parent=None, objid=None, url=None, data=None, poll_interval=None,
                 auth=None, timeout=None):
        """
        :param parent:              parent jenkins object
        :param objid:               object id in parent context (artifact relative path)
        :param url:                 jenkins URL, api/python will be added to the end
        :param data:                we already got the data, so initiate the object with the data
        :param auth:                jenkins auth - either apitoken or username and pwd
        :param timeout:             timeout for API calls
        :param url:                 jenkins URL, api/python will be added to the end
        :param poll_interval:       0 - data polled al  ways when value requested
                                    >0 - interval in which data are refreshed (in seconds)
                                    None - data automatically polled only once, when data are accessed
        """
        super(JenkinsArtifacts, self).__init__(
            parent=parent,
            objid='artifacts',
            url=url,
            data=data,
            poll_interval=poll_interval,
            auth=auth,
            timeout=timeout)

        # populate self._artifacts
        self._update_data(self._data)

    def _update_data(self, data, now=None):
        """
        Data update, should be overridden in subclasses
        :param now:     update timestamp
        """
        if not hasattr(self, '_artifact'):
            # we have not initialize it yet
            self._artifacts = {}

        self._data = data
        _artifacts = {}
        for artifact in self._data:
            _artifacts[artifact['relativePath']] = Artifact(
                    displaypath=artifact['displayPath'],
                    filename=artifact['fileName'],
                    relativepath=artifact['relativePath'],
                    parent=self
                )

        # merge artifacts, first calculate keys to delete
        # then delete keys in self._artifacts, then update local _artifacts from self._artifacts
        # and then update self._artifacts (this is done just to keep object id of self._artifacts the same ...)
        current = set(self._artifacts.keys())
        new = set(_artifacts.keys())
        intersection = set.intersection(current, new)
        for key in current - intersection:
            del self._artifacts[key]
        # we do not to override any already retrieved artifact content
        _artifacts.update(self._artifacts)
        self._artifacts.update(_artifacts)
        return self

    def iteritems(self, filterfn=None):
        """
        Generator providing artifact objects, but only those where filterfn returns True
        :param  (str|unicode) -> bool filterfn:
        :return:
        """
        # first copy artifacts to prevent autoudpates to mess with iteration
        artifacts = dict(self._artifacts)
        if filterfn is None:
            filterfn = lambda x: True

        for key in artifacts.iterkeys():
            if filterfn(key):
                yield key, artifacts[key]

    @property
    def artifacts(self):
        self.auto_poll()
        return self._artifacts

    def _poll(self):
        """
        We have to in reality poll job having artifacts ....
        In our case parent should always be a JenkinsBuild instance ...
        :return:
        """
        self.parent._poll()
        self._data = self.parent._data['artifacts']
        return self

    def writeall(self, basepath=None, filter_artifacts=None, path_transform=None):
        """
        Writes all artifacts to disk, relatively to basepath

        :param (str|unicode) -> bool filter_artifacts:  callable for filtering artifacts to be downloaded
        :param str|unicode basepath:            where to store artifacts, all wiil be stored relative to this path
        :param (str|unicode) -> str|unicode path_transform:      callable transforming artifact relative path
        :return:
        """

        if filter_artifacts is None:
            # default is to download all
            filter_artifacts = lambda x: True

        if path_transform is None:
            # default is no transform
            path_transform = lambda x: x

        if basepath is None:
            # we default to cwd ...
            basepath = os.path.curdir

        for relpath, artifact in self.iteritems(filter_artifacts):
            fullpath = os.path.normpath(os.path.join(basepath, *path_transform(relpath).split('/')))
            dirname = os.path.dirname(fullpath)
            # create directory, if it does not exists
            if dirname != '' and not os.path.exists(dirname):
                os.makedirs(dirname)

            artifact.write(fullpath)
            logger.info(' Artifact "%s" downloaded to "%s".' % (relpath, fullpath))

        return self
