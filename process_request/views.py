from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from rest_framework.viewsets import ModelViewSet
from .models import MachineUser
from .serializers import MachineUserSerializer

# Create your views here.
class MachineUserViewSet(ModelViewSet):
    model = MachineUser
    queryset = MachineUser.objects.all()
    serializer_class = MachineUserSerializer

    pass
    def machineuser_list(request):
        if request.method == 'GET':
            users = MachineUser.objects.all()
            serializer = MachineUserSerializer(users, many=True)
            return JsonResponse(serializer.data, safe=False)

    def machineuser_detail(request, pk):
        try:
            machineuser = MachineUser.objects.get(pk=pk)
        except MachineUser.DoesNotExist:
            return HttpResponse(status=404)

        if request.method = 'GET':
            serializer = MachineUserSerializer(machineuser)
            return JsonResponse(serializer.data)
