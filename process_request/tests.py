from django.test import TestCase
from django.urls import reverse
from os.path import join
from rest_framework.test import APIRequestFactory
import vcr

from request_broker import settings
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


class TestViews(TestCase):

    def test_processrequestview(self):
        factory = APIRequestFactory()
        request = factory.post(reverse('process-request'), {"items": ["/repositories/2/archival_objects/8457"]}, format='json')
        response = ProcessRequestView.as_view()(request)
        self.assertEqual(response.status_code, 200)
