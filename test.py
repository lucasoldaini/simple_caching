import os
from simple_caching import simple_caching


@simple_caching(cachedir='cache')
def Foo(foo):
    return {'foo': foo}

if __name__ == '__main__':
    if not os.path.exists('cache'):
        os.makedirs('cache')
    else:
        empty_memcache = ((raw_input('flush cache? [y/N]: ') == 'y')
                          and True) or False
        if empty_memcache:
            for f in os.listdir('cache'):
                os.remove(os.path.join('cache', f))

    print Foo('gzip: bar', cache_format='gzip')
    print Foo('gzip: bar', cache_format='gzip')

    print Foo('json: bar', cache_format='json')
    print Foo('json: bar', cache_format='json')

