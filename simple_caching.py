"""Caching decorator for dictionary/tuples."""

import json
import os
from functools import wraps
import gzip
import sys
from string import punctuation
import codecs
from hashlib import md5

_OK_JSON = set((dict, list, str, int, float))


class _DumpAdapter(object):
    """ Flexible interlace to blindly use codecs module or
        gzip module
    """
    def __init__(self, func, accepted_args):
        self.func = func
        self.accepted_args = accepted_args

    def __call__(self, **kwargs):
        keyword_arguments = {k: kwargs[k] for k in kwargs
                             if k in self.accepted_args}
        return self.func(**keyword_arguments)


def simple_caching(cachedir=None,
                   mode=None,
                   cache_comment=None,
                   force_refresh=False,
                   cache_format='gzip'):
    """ Caching decorator for dictionary/tuples.

    Caches gzipped json in specified cache folder

    Accepts the following kwargs:

    mode (default='hash')
    accepted modes:
        (1) method-name: the name of the decorated method
            is used as name for the cache.
        (2) hash: a hash of the parameters is used as
            name of the cache

    cachedir (default=None)
    Location of the folder where to cache. cachedir
    doesn't need to be configured if simple_caching
    is caching a method of a class with cachedir attribute.

    cache_comment (default=None)
    A comment to add to the name of the cache.
    If no comment is provided, the name of the cache
    if the name of the method that is being cachedonly.

    force_refresh (default=False)
    rebuilts cache if set to True

    cache_format (default=gzip)
    it could either be gzip or json

    The kwargs can be set either (a) at decoration time
    or (b) when the decorated method is called:

    example (a):
    @simple_caching(cachedir='/path/to/cache')
    def foo(s):
    ...

        example (b):
        @simple_caching()
        def foo(s):
    ...
        ...

        foo('baz', cachedir='/path/to/cache')

        A combination of both is also fine, of course.
        kwargs provided at call time have precedence, though.
    """
    # Without the use of this decorator factory,
    # the name of the method would have been 'wrapper'
    # and the docstring of the original method would have been lost.
    #       from python docs:
    #       https://docs.python.org/2/library/functools.html#module-functools

    def caching_decorator(method):
        # cachedir, cache_comment and autodetect are out
        # of scope for method_wrapper, thus local variables
        # need to be instantiated.
        local_cachedir = cachedir
        local_cache_comment = (cache_comment or '')
        local_force_refresh = force_refresh
        local_cache_format = cache_format
        local_mode = mode

        if local_mode is None:
            local_mode = 'hash'

        if (local_mode not in ('hash', 'method-name')):
            print >> sys.stderr, ("[cache error] '{0}' is not " +
                                  "a valid caching mode; use 'method-name' " +
                                  "or 'hash'.").format(local_mode)
            sys.exit(1)

        @wraps(method)
        def method_wrapper(*args, **kwargs):

            # looks for cachedir folder in self instance
            # if not found, it looks for it in keyword
            # arguments.
            try:
                cachedir = args[0].cachedir
            except AttributeError:
                    cachedir = kwargs.pop('cachedir', local_cachedir)

            # if no cachedir is specified, then it simply returns
            # the original method and does nothing
            if not cachedir:
                return method(*args, **kwargs)

            # checks if the global parameters are overwritten by
            # values @ call time or if some of the missing parameters
            # have been provided at call time
            cache_comment = kwargs.pop('cache_comment', local_cache_comment)
            force_refresh = kwargs.pop('force_refresh', local_force_refresh)
            mode = kwargs.pop('mode', ((local_mode is not None) and
                                       local_mode) or 'hash')

            if not os.path.exists(cachedir):
                cachedir = os.path.join(os.getcwd(), cachedir)
                if not os.path.exists(cachedir):
                    print >> sys.stderr, ("[cache error] {0} is not " +
                                          "a valid dir.").format(cachedir)
                    sys.exit(1)

            cache_format = kwargs.pop('cache_format', local_cache_format)
            if cache_format == 'json':
                dump_func = _DumpAdapter(codecs.open,
                                         ['filename', 'mode', 'encoding'])
                ext = 'json'
            elif cache_format == 'gzip':
                dump_func = _DumpAdapter(gzip.open,
                                         ['filename', 'mode'])
                ext = 'gz'
            else:
                print >> sys.stderr, ("[cache error] {0} is not a valid " +
                                      "cache format. Use json or gzip." +
                                      "").format(cache_format)
                sys.exit(1)

            if mode == 'method-name':
                name = method.__name__
            if mode == 'hash':
                to_hash = json.dumps({'args': [a for a in args
                                               if a in _OK_JSON],
                                     'kwargs': {k: v for k, v in kwargs.items()
                                                if v in _OK_JSON}
                                      })
                name = md5(to_hash).hexdigest()

            # the ...and...or... makes sure that there is an underscore
            # between cache file name and cache comment if cache_comment
            # exists.
            cachename = '%s%s.cache.%s' % (name,
                                           (cache_comment and
                                            '_%s' % cache_comment) or '',
                                           ext)
            # removes prefix/suffix punctuation from method name
            # (e.g. __call__ will become call)
            while cachename[0] in punctuation:
                cachename = cachename[1:]
            while cachename[(len(cachename) - 1)] in punctuation:
                cachename = cachename[:(len(cachename) - 1)]
            cachepath = os.path.join(cachedir, cachename)

            # loads creates cache
            if os.path.exists(cachepath) and not force_refresh:
                with dump_func(filename=cachepath,
                               mode='r', encoding='utf-8') as cachefile:
                    return json.loads(cachefile.read())
            else:
                print '[cache] generating %s' % cachepath
                tocache = method(*args, **kwargs)
                with dump_func(filename=cachepath, mode='w',
                               encoding='utf-8') as cachefile:
                    try:
                        json.dump(tocache, cachefile)
                    except TypeError:
                        cachefile.close()
                        os.remove(cachepath)
                        raise
                return tocache
        return method_wrapper
    return caching_decorator
