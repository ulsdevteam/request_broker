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
        print(ProcessRequest().message)
        return Response(str(ProcessRequest()), status=200)
