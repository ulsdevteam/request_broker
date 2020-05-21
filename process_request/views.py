from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView

from .models import MachineUser
from .routines import ProcessRequest

# Create your views here.
class ProcessRequestView(APIView):
    '''
    Calls the ProcessRequest class from routines.
    '''
    request = ProcessRequest()
