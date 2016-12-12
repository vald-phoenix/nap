from __future__ import unicode_literals
import itertools
import six
from six.moves.urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def normalize_url(url_string):
    url = urlsplit(url_string)
    if url.query:
        query_params = sorted(parse_qsl(url.query, keep_blank_values=True), key=lambda key_value: key_value[0])
        query_normalized = urlencode(query_params)
        url = url._replace(query=query_normalized)

    # urlsplit'ing and urlunsplit'ing does some normalization, so apply them even if there is not a query string.
    # See https://docs.python.org/2/library/urlparse.html#urlparse.urlunsplit for more details.
    return urlunsplit(url)


def handle_slash(url, add_slash=None):
    split = url.split('?')

    if add_slash and not split[0].endswith('/'):
        if len(split) > 1:
            url = "%s/?%s" % (split[0], split[1])
        else:
            url = "%s/" % url
    elif add_slash is False and split[0].endswith('/'):
        if len(split) > 1:
            url = "%s?%s" % (split[0][:-1], split[1])
        else:
            url = split[0][:-1]

    return url


def is_string_like(obj):
    return isinstance(obj, six.string_types)


def make_url(base_url, params=None, add_slash=None):
    "Split off in case we need to handle more scrubing"

    base_url = handle_slash(base_url, add_slash)

    if params:

        def safe_encode(value):
            if isinstance(value, six.text_type):
                return value.encode('utf-8')
            return value

        # If we're given an non-string iterable as a params value,
        # we want to pass in multiple instances of that param key.
        def flatten_params(k, vs):
            if not hasattr(vs, '__iter__') or is_string_like(vs):
                return ((k, safe_encode(vs)),)
            return [(k, safe_encode(v)) for v in vs]

        flat_params = [
            flatten_params(k, v)
            for (k, v) in params.items()
        ]

        # since we can have more than one value for a single key, we use a
        # tuple of two tuples instead of a dictionary
        params_tuple = tuple(itertools.chain(*flat_params))
        param_string = urlencode(params_tuple)
        base_url = "%s?%s" % (base_url, param_string)

    return base_url


__text_fn = str if six.PY3 else unicode


def to_unicode(s):
    if s is None:
        return None

    # unicode strings
    elif isinstance(s, six.text_type):
        return s

    # non-unicode strings
    elif isinstance(s, six.binary_type):
        return __text_fn(s, 'utf-8')

    # non-string types
    else:
        return __text_fn(s)
