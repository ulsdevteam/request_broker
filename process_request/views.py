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
        request = ['/repositories/2/archival_objects/1154299']
        return Response(str(ProcessRequest.get_object(self, request)), status=200)
