from os.path import join

import vcr
from django.test import TestCase
from django.urls import reverse
from request_broker import settings
from rest_framework.test import APIRequestFactory

from .models import MachineUser, User
from .routines import ProcessRequest
from .views import ProcessRequestView

transformer_vcr = vcr.VCR(
    serializer='json',
    cassette_library_dir=join(settings.BASE_DIR, 'fixtures/cassettes'),
    record_mode='once',
    match_on=['path', 'method'],
    filter_query_parameters=['username', 'password'],
    filter_headers=['Authorization', 'X-ArchivesSpace-Session'],
)

ROUTINES = (
    ('process_request.json', ProcessRequest),
)

VIEWS = (
    ('process_request.json', ProcessRequestView),
)


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
        for cassette, routine in ROUTINES:
            with transformer_vcr.use_cassette(cassette):
                routines = ProcessRequest().run(['/repositories/2/archival_objects/8457'])
                self.assertEqual(routines.status_code, 200)


class TestViews(TestCase):

    def test_processrequestview(self):
        factory = APIRequestFactory()
        for v in VIEWS:
            with transformer_vcr.use_cassette(v[0]):
                request = factory.post(reverse('process-request'), {"items": ["/repositories/2/archival_objects/8457"]}, format='json')
                response = v[1].as_view()(request)
                self.assertEqual(response.status_code, 200)
