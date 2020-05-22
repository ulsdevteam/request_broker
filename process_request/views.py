from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView

from .routines import ProcessRequest

# Create your views here.
class ProcessRequestView(APIView):
    '''
    Calls the ProcessRequest class from routines.
    '''
    def get(self, request, format=None):
        print('hi')
        request = ['one','two']
        return Response(str(ProcessRequest.unpack_request(self, request)), status=200)
