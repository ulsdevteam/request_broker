from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView

from .models import MachineUser
from .serializers import MachineUserSerializer
from .routines import ProcessRequest

# Create your views here.
class ProcessRoutinesView(APIView):
    def post(self, request, format=None):
        try:
            response = self.routine().run()
            return Response(prepare_response(response), status=200)
        except Exception as e:
            return Response(prepare_response(e), status=500)

class ProcessRequestsView(ProcessRoutinesView):
    """Runs the ProcessRequest routine. Accepts POST requests only."""
    routine = ProcessRequest
