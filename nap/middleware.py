from __future__ import unicode_literals

class BaseMiddleware(object):

    def handle_request(self, request):
        return request

    def handle_response(self, request, response):
        return response
