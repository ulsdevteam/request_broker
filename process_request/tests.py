import csv
from datetime import date
from os.path import join
from unittest.mock import patch

import vcr
from django.core import mail
from django.http import StreamingHttpResponse
from django.test import TestCase
from django.urls import reverse
from request_broker import settings
from rest_framework.test import APIRequestFactory
from rest_framework_api_key.models import APIKey

from .clients import AeonAPIClient
from .helpers import (get_container_indicators, get_dates, get_file_versions,
                      get_instance_data, get_locations, get_preferred_format,
                      get_resource_creator, prepare_values)
from .models import User
from .routines import AeonRequester, Mailer, Processor
from .test_helpers import json_from_fixture, random_list, random_string
from .views import (DeliverDuplicationRequestView,
                    DeliverReadingRoomRequestView, DownloadCSVView, MailerView,
                    ParseRequestView, ProcessEmailRequestView)

aspace_vcr = vcr.VCR(
    serializer='json',
    cassette_library_dir=join(settings.BASE_DIR, 'fixtures/cassettes'),
    record_mode='once',
    match_on=['path', 'method'],
    filter_query_parameters=['username', 'password'],
    filter_headers=['Authorization', 'X-ArchivesSpace-Session'],
)


class TestUsers(TestCase):

    def test_user(self):
        user = User(
            first_name="Patrick",
            last_name="Galligan",
            email="pgalligan@rockarch.org")
        self.assertEqual(user.full_name, "Patrick Galligan")
        self.assertEqual(str(user), "Patrick Galligan <pgalligan@rockarch.org>")


class TestHelpers(TestCase):

    def test_get_resource_creator(self):
        obj_data = json_from_fixture("object_all.json")
        self.assertEqual(get_resource_creator(obj_data.get("ancestors")[-1].get("_resolved")), "Philanthropy Foundation")

    def test_get_dates(self):
        obj_data = json_from_fixture("object_all.json")
        self.assertEqual(get_dates(obj_data), "1991")

        obj_data = json_from_fixture("object_no_expression.json")
        self.assertEqual(get_dates(obj_data), "1991-1992")

        obj_data = json_from_fixture("object_no_expression_no_end.json")
        self.assertEqual(get_dates(obj_data), "1993")

    def test_get_container_indicators(self):
        letters = random_string(10)
        expected_title = "Digital Object: {}".format(letters)
        item = {'instances': [{'instance_type': 'digital_object', 'digital_object': {'_resolved': {'title': letters}}}]}
        self.assertEqual(get_container_indicators(item), expected_title)

        type = random_string(10)
        number = random_string(2)
        item = {'instances': [{'instance_type': 'mixed materials', 'sub_container':
                               {'top_container': {'_resolved': {'type': type, 'indicator': number}}}}]}
        expected_indicator = "{} {}".format(type.capitalize(), number)
        self.assertEqual(get_container_indicators(item), expected_indicator)

        type = random_string(10)
        number = random_string(2)
        letters = random_string(10)
        item = {'instances': [{'instance_type': 'mixed materials', 'sub_container':
                               {'top_container': {'_resolved': {'type': type, 'indicator': number}}}},
                              {'instance_type': 'digital_object', 'digital_object': {'_resolved': {'title': letters}}}]}
        expected_containers = "{} {}, Digital Object: {}".format(type.capitalize(), number, letters)
        self.assertEqual(get_container_indicators(item), expected_containers)

        item = {'instances': []}
        self.assertEqual(get_container_indicators(item), None)

    def test_get_file_versions(self):
        uri = random_string(10)
        digital_object = {'file_versions': [{'file_uri': uri}]}
        self.assertEqual(get_file_versions(digital_object), uri)

    def test_get_locations(self):
        obj_data = json_from_fixture("locations.json")
        expected_location = "Rockefeller Archive Center, Blue Level, Vault 106 [Unit:  66, Shelf:  7]"
        self.assertEqual(get_locations(obj_data), expected_location)

    def test_get_instance_data(self):
        obj_data = json_from_fixture("digital_object_instance.json")
        expected_values = ("digital_object", "Digital Object: digital object", "http://google.com", "238475")
        self.assertEqual(get_instance_data([obj_data]), expected_values)

        obj_data = json_from_fixture("mixed_materials_instance.json")
        expected_values = ("mixed materials", "Box 2",
                           "Rockefeller Archive Center, Blue Level, Vault 106 [Unit:  66, Shelf:  7]",
                           "A12345")
        self.assertEqual(get_instance_data([obj_data]), expected_values)

    def test_get_preferred_format(self):
        obj_data = json_from_fixture("object_digital.json")
        expected_data = ("digital_object", "Digital Object: digital object, Digital Object: digital object 2",
                         "http://google.com, http://google2.com", "238475, 238476")
        self.assertEqual(get_preferred_format(obj_data), expected_data)

        obj_data = json_from_fixture("object_microform.json")
        expected_data = ("microform",
                         "Reel 1, Reel 2",
                         "Rockefeller Archive Center, Blue Level, Vault 106 [Unit:  66, Shelf:  7], Rockefeller Archive Center, Blue Level, Vault 106 [Unit:  66, Shelf:  8]",
                         "A12345, A123456")
        self.assertEqual(get_preferred_format(obj_data), expected_data)

        obj_data = json_from_fixture("object_mixed.json")
        expected_data = ("mixed materials",
                         "Box 1, Box 2",
                         "Rockefeller Archive Center, Blue Level, Vault 106 [Unit:  66, Shelf:  7], Rockefeller Archive Center, Blue Level, Vault 106 [Unit:  66, Shelf:  8]",
                         "A12345, A123456")
        self.assertEqual(get_preferred_format(obj_data), expected_data)

        obj_data = json_from_fixture("object_no_instance.json")
        expected_data = (None, None, None, None)
        self.assertEqual(get_preferred_format(obj_data), expected_data)

    def test_prepare_values(self):
        values_list = [["mixed materials", "mixed materials", None],
                       ["Reel 1", "Box 2", None, "Reel 2"],
                       ["Shelf 1", None, "Shelf 2"],
                       ["A0001", "A0002", "A0003"]
                       ]
        expected_parsed = ("mixed materials", "Reel 1, Box 2, Reel 2",
                           "Shelf 1, Shelf 2",
                           "A0001, A0002, A0003",
                           )
        self.assertEqual(prepare_values(values_list), expected_parsed)

        values_list = [[None], [None], [None], [None]]
        expected_parsed = (None, None, None, None)
        self.assertEqual(prepare_values(values_list), expected_parsed)

    def test_aeon_client(self):
        baseurl = random_string(20)
        client = AeonAPIClient(baseurl)
        self.assertEqual(client.baseurl, baseurl)
        self.assertEqual(client.session.headers.get("X-AEON-API-KEY"), settings.AEON_API_KEY)


class TestRoutines(TestCase):

    @patch("process_request.routines.Processor.get_data")
    def test_parse_items(self, mock_get_data):
        item = json_from_fixture("as_data.json")
        mock_get_data.return_value = item
        for restrictions, text, submit, reason in [
                ("closed", "foo", False, "Item is restricted: foo"),
                ("open", "bar", True, None),
                ("conditional", "foobar", True, None)]:
            mock_get_data.return_value["restrictions"] = restrictions
            mock_get_data.return_value["restrictions_text"] = text
            parsed = Processor().parse_items([mock_get_data.return_value])[0]
            self.assertEqual(parsed["submit"], submit)
            self.assertEqual(parsed["submit_reason"], reason)
        for format, submit in [
                ("Digital", False), ("Mixed materials", True), ("microfilm", True)]:
            mock_get_data.return_value["preferred_format"] = format
            parsed = Processor().parse_items([item])[0]
            self.assertEqual(parsed["submit"], submit)

    @patch("process_request.routines.Processor.get_data")
    def test_process_email_request(self, mock_get_data):
        mock_get_data.return_value = json_from_fixture("as_data.json")
        to_process = random_list()
        processed = Processor().process_email_request(to_process)
        self.assertEqual(len(to_process), len(processed))
        self.assertTrue([isinstance(item, dict) for item in processed])

    def test_deliver_email(self):
        object_list = [json_from_fixture("as_data.json")]
        for to, subject in [
                ("test@example.com", "Subject"),
                (["foo@example.com", "bar@example.com"], None)]:
            expected_to = to if isinstance(to, list) else [to]
            emailed = Mailer().send_message(to, object_list, subject)
            self.assertEqual(emailed, "email sent to {}".format(", ".join(expected_to)))
            self.assertTrue(isinstance(mail.outbox[0].to, list))
            self.assertIsNot(mail.outbox[0].subject, None)
            self.assertNotIn("location", mail.outbox[0].body)
            self.assertNotIn("barcode", mail.outbox[0].body)

    @aspace_vcr.use_cassette("aspace_request.json")
    def test_get_data(self):
        get_as_data = Processor().get_data("/repositories/2/archival_objects/1134638")
        self.assertTrue(isinstance(get_as_data, dict))
        self.assertEqual(len(get_as_data), 14)

    @patch("requests.Session.post")
    def test_send_aeon_requests(self, mock_post):
        return_str = random_string(10)
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = return_str
        items = json_from_fixture("as_data.json")
        data = {"scheduled_date": date.today().isoformat(), "items": [items]}
        delivered = AeonRequester().send_request("readingroom", **data)
        self.assertEqual(delivered, return_str)

        data["format"] = "jpeg"
        delivered = AeonRequester().send_request("duplication", **data)
        self.assertEqual(delivered, return_str)

        request_type = "foo"
        with self.assertRaises(Exception, msg="Unknown request type '{}', expected either 'readingroom' or 'duplication'".format(request_type)):
            AeonRequester().send_request(request_type, **data)


class TestViews(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.apikey = APIKey.objects.create_key(name="test-service")[1]

    def assert_handles_routine(self, request_data, view_str, view):
        request = self.factory.post(
            reverse(view_str), request_data, format="json")
        request.META.update({"HTTP_X_REQUEST_BROKER_KEY": self.apikey})
        response = view.as_view()(request)
        self.assertEqual(response.status_code, 200, "Response error: {}".format(response.data))
        self.assertEqual(len(response.data), 1)

    def assert_handles_exceptions(self, patched_fn, exception_text, view_str, view):
        patched_fn.side_effect = Exception(exception_text)
        request = self.factory.post(
            reverse(view_str), {"items": random_list()}, format="json")
        request.META.update({"HTTP_X_REQUEST_BROKER_KEY": self.apikey})
        response = view.as_view()(request)
        self.assertEqual(
            response.status_code, 500, "Request did not return a 500 response")
        self.assertEqual(
            response.data["detail"], exception_text, "Exception string not in response")

    @patch("process_request.routines.Processor.get_data")
    def test_download_csv_view(self, mock_get_data):
        mock_get_data.return_value = json_from_fixture("as_data.json")
        to_process = random_list()
        request = self.factory.post(
            reverse("download-csv"), {"items": to_process}, format="json")
        request.META.update({"HTTP_X_REQUEST_BROKER_KEY": self.apikey})
        response = DownloadCSVView.as_view()(request)
        self.assertTrue(isinstance(response, StreamingHttpResponse))
        self.assertEqual(response.get('Content-Type'), "text/csv")
        self.assertIn("attachment;", response.get('Content-Disposition'))
        f = response.getvalue().decode("utf-8")
        reader = csv.reader(f.splitlines())
        self.assertEqual(
            sum(1 for row in reader), len(to_process) + 1,
            "Incorrect number of rows in CSV file")

        self.assert_handles_exceptions(
            mock_get_data, "foobar", "download-csv", DownloadCSVView)

    @patch("process_request.routines.Processor.process_email_request")
    def test_process_email_request_view(self, mock_processed):
        mock_processed.return_value = [json_from_fixture("as_data.json")]
        self.assert_handles_routine(
            {"items": random_list()}, "process-email", ProcessEmailRequestView)
        self.assert_handles_exceptions(
            mock_processed, "foobar", "process-email", ProcessEmailRequestView)

    @patch("process_request.routines.Mailer.send_message")
    def test_send_email_request_view(self, mock_sent):
        mock_sent.return_value = "email sent"
        self.assert_handles_routine(
            {"items": random_list(), "to_address": "test@example.com", "subject": "DIMES list"},
            "deliver-email",
            MailerView)
        self.assert_handles_exceptions(
            mock_sent, "foobar", "process-email", MailerView)

    @patch("process_request.routines.Processor.parse_items")
    def test_parse_request_view(self, mock_parse):
        parsed = random_list()
        mock_parse.return_value = parsed
        self.assert_handles_routine(
            {"items": parsed}, "parse-request", ParseRequestView)
        self.assert_handles_exceptions(
            mock_parse, "bar", "parse-request", ParseRequestView)

    @patch("process_request.routines.AeonRequester.send_request")
    def test_deliver_readingroomrequest_view(self, mock_send):
        delivered = random_list()
        mock_send.return_value = delivered
        self.assert_handles_routine(
            {"items": delivered, "scheduled_date": date.today().isoformat()},
            "deliver-readingroom", DeliverReadingRoomRequestView)
        self.assert_handles_exceptions(
            mock_send, "bar", "deliver-readingroom", DeliverReadingRoomRequestView)

    @patch("process_request.routines.AeonRequester.send_request")
    def test_deliver_duplicationrequest_view(self, mock_send):
        delivered = random_list()
        mock_send.return_value = delivered
        self.assert_handles_routine(
            {"items": delivered, "format": "jpeg"},
            "deliver-duplication", DeliverDuplicationRequestView)
        self.assert_handles_exceptions(
            mock_send, "bar", "deliver-duplication", DeliverDuplicationRequestView)
