"""
Sphinx plugins for nap documentation.
"""
from __future__ import unicode_literals


def setup(app):
    app.add_crossref_type(
        directivename="option",
        rolename="option",
        indextemplate="pair: %s; option",
    )
    app.add_crossref_type(
        directivename="method",
        rolename="method",
        indextemplate="pair: %s; method",
    )
