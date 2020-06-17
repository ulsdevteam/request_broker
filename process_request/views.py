from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView

from .routines import ProcessRequest

# Create your views here.
class ProcessRequestView(APIView):
    '''
    Calls the ProcessRequest class from routines.
    '''
    def post(self, request, format=None):
        object_list = request.data.get('items')
        process_list = ProcessRequest().run(object_list)
        print(process_list)
        return Response(process_list, status=200)
