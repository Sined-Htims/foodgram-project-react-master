from django.db import IntegrityError
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response


class InterceptorIntegrityErrorMiddleware:
    '''Middleware, для перехвата ошибки IntegrityError, во всем проекте.'''
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, IntegrityError):
            response = Response(
                {'error': 'Ошибка взаимодействовали с БД проверьте данные'},
                status=status.HTTP_400_BAD_REQUEST
            )
            response.accepted_renderer = JSONRenderer()
            response.accepted_media_type = JSONRenderer.media_type
            response.renderer_context = {'request': request}
            return response
