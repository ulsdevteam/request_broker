import csv
import json
import random
import string
from os.path import join
from unittest.mock import patch

import vcr
from django.http import StreamingHttpResponse
from django.test import TestCase
from django.urls import reverse
from request_broker import settings
from rest_framework.test import APIRequestFactory

from .models import MachineUser, User
from .routines import ProcessRequest
from .views import DownloadCSVView, ProcessRequestView

transformer_vcr = vcr.VCR(
    serializer='json',
    cassette_library_dir=join(settings.BASE_DIR, 'fixtures/cassettes'),
    record_mode='once',
    match_on=['path', 'method'],
    filter_query_parameters=['username', 'password'],
    filter_headers=['Authorization', 'X-ArchivesSpace-Session'],
)

FIXTURES_DIR = join(settings.BASE_DIR, "fixtures")

ROUTINES = (
    ('process_request.json', ProcessRequest),
)

VIEWS = (
    ('process_request.json', ProcessRequestView),
)

item_list = ['/repositories/2/archival_objects/1154382',
             '/repositories/2/archival_objects/1154384',
             '/repositories/2/archival_objects/1154385',
             '/repositories/2/archival_objects/1154386',
             '/repositories/2/archival_objects/1154387'
            ]

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
                for item in item_list:
                    get_data = ProcessRequest().get_data(item)
                    #routines = ProcessRequest().process_readingroom_request('/repositories/2/archival_objects/8457')
                    #self.assertEqual(routines, 'test')


class TestViews(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_processrequestview(self):
        for v in VIEWS:
            with transformer_vcr.use_cassette(v[0]):
                request = self.factory.post(reverse('process-request'), {"items": item_list}, format='json')
                response = v[1].as_view()(request)
                self.assertEqual(response.status_code, 200)

    @patch("process_request.routines.ProcessRequest.get_data")
    def test_downloadcsvview(self, mock_get_data):
        with open(join(FIXTURES_DIR, "as_data.json"), "r") as df:
            item = json.load(df)
            mock_get_data.return_value = item
            to_process = random.sample(string.ascii_lowercase, random.randint(2, 10))
            request = self.factory.post(
                reverse("download-csv"), {"items": to_process}, format="json")
            response = DownloadCSVView.as_view()(request)
            self.assertTrue(isinstance(response, StreamingHttpResponse))
            self.assertEqual(response.get('Content-Type'), "text/csv")
            self.assertIn("attachment;", response.get('Content-Disposition'))
            f = response.getvalue().decode("utf-8")
            reader = csv.reader(f.splitlines())
            self.assertEqual(
                sum(1 for row in reader), len(to_process) + 1,
                "Incorrect number of rows in CSV file")

            mock_get_data.side_effect = Exception("foobar")
            to_process = random.sample(string.ascii_lowercase, random.randint(2, 10))
            request = self.factory.post(
                reverse("download-csv"), {"items": to_process}, format="json")
            response = DownloadCSVView.as_view()(request)
            self.assertEqual(
                response.status_code, 500, "Request did not return a 500 response")
            self.assertEqual(
                response.data["detail"], "foobar", "Exception string not in response")
