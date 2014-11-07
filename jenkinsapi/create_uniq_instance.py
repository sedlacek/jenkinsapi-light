__author__ = 'sedlacek'


class __create_unique_instance(object):
    """
    Create unique class instance
    """

    def __init__(self):
        self.objects = {}

    def __call__(self, class_, *args, **kwargs):
        """
        Create new instance of class_, but if already exists it is discarded ...
        and existing instance is used
        """
        class_name = class_.__name__
        having_key = False
        if class_name not in self.objects:
            self.objects[class_name] = {}

        try:
            key = self._get_key_from_args(*args, **kwargs)
            having_key = True
            return self.objects[class_name][key]

        except KeyError:
            instance = class_(*args, **kwargs)
            if not having_key:
                try:
                    key = self._get_key_from_instance(instance)
                except KeyError:
                    # we cannot dig out the key from instance :(
                    # just return class instance
                    return instance
            try:
                return self.objects[class_name][key]
            except KeyError:
                # we did not find object in the cache, so add it to cache
                # and return the instance
                self.objects[class_name][key] = instance
                return instance

    def _get_key_from_args(self, *args, **kwargs):
        """
        Should raise KeyError exception if no key is in args
        """
        raise NotImplementedError

    def _get_key_from_instance(self, instance):
        """
        Should raise KeyError exception if the key is not found in instance
        """
        raise NotImplementedError


class __create_unique_jenkins_instance(__create_unique_instance):

    def _get_key_from_args(self, *args, **kwargs):
        key = kwargs['url']
        if key is None:
            raise KeyError
        return key

    def _get_key_from_instance(self, instance):
        try:
            return instance.url
        except:
            raise KeyError

new = __create_unique_jenkins_instance()


if __name__ == '__main__':

    class Test(object):
        def __init__(self, url=None):
            pass

    class NoURL(object):
        def __init__(self, fake=None):
            self.url = fake

    class Broken(object):
        pass

    i1 = new(Test, url='1234')
    i2 = new(Test, url='1234')
    i3 = new(Test, url='12345')

    i4 = new(NoURL, fake='1234')
    i5 = new(NoURL, fake='1234')
    i6 = new(NoURL, fake='12345')


    i7 = new(Broken)
    i8 = new(Broken)
    i9 = new(Broken)

    print 'end'
