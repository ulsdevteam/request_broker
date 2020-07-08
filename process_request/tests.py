from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from .models import MachineUser, User
from .routines import ProcessRequest
from .views import ProcessRequestView


class TestUsers(TestCase):

    def test_user(self):
        user = User(
            first_name="Patrick",
            last_name="Galligan",
            email="pgalligan@rockarch.org")
        self.assertEqual(user.full_name, "Patrick Galligan")
        self.assertEqual(str(user), "Patrick Galligan <pgalligan@rockarch.org>")

    def test_machineuser(self):
        system = 'Zodiac'
        user = MachineUser(system_name="Zodiac")
        self.assertEqual(str(user), system)


class TestRoutines(TestCase):

    def test_routines(self):
        routines = ProcessRequest().run(['/repositories/2/archival_objects/8457'])
        print(routines)


class TestViews(TestCase):

    def test_processrequestview(self):
        factory = APIRequestFactory()
        request = factory.post(reverse('process-request'), {"items": ["/repositories/2/archival_objects/8457"]}, format='json')
        response = ProcessRequestView.as_view()(request)
        self.assertEqual(response.status_code, 200)
