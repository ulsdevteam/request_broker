import csv
from datetime import date
from os.path import join
from unittest.mock import ANY, patch

import vcr
from asnake.aspace import ASpace
from django.conf import settings
from django.core import mail
from django.http import StreamingHttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from .helpers import (get_container_indicators, get_dates, get_file_versions,
                      get_formatted_resource_id, get_instance_data,
                      get_locations, get_parent_title, get_preferred_format,
                      get_resource_creators, get_restricted_in_container,
                      get_rights_info, get_rights_status, get_rights_text,
                      get_size, indicator_to_integer, prepare_values)
from .models import User
from .routines import AeonRequester, Mailer, Processor
from .test_helpers import json_from_fixture, random_list, random_string
from .views import (DeliverDuplicationRequestView,
                    DeliverReadingRoomRequestView, DownloadCSVView, MailerView,
                    ParseBatchRequestView, ParseItemRequestView)

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

    @aspace_vcr.use_cassette("aspace_request.json")
    def setUp(self):
        self.client = ASpace(baseurl=settings.ARCHIVESSPACE["baseurl"],
                             username=settings.ARCHIVESSPACE["username"],
                             password=settings.ARCHIVESSPACE["password"],
                             repository=settings.ARCHIVESSPACE["repo_id"]).client

    @patch("asnake.client.web_client.ASnakeClient")
    def test_get_resource_creators(self, mock_client):
        mock_client.get.return_value.json.return_value = {"results": [{"title": "Philanthropy Foundation"}]}
        obj_data = json_from_fixture("object_all.json")
        self.assertEqual(get_resource_creators(obj_data.get("ancestors")[-1].get("_resolved"), mock_client), "Philanthropy Foundation")
        mock_client.get.assert_called_with('/repositories/2/search?fields[]=title&type[]=agent_person&type[]=agent_corporate_entity&type[]=agent_family&page=1&q="/agents/corporate_entities/123"')

    def test_get_dates(self):
        obj_data = json_from_fixture("object_all.json")
        self.assertEqual(get_dates(obj_data, self.client), None)

        obj_data = json_from_fixture("object_no_expression.json")
        self.assertEqual(get_dates(obj_data, self.client), "1991-1992")

        obj_data = json_from_fixture("object_no_expression_no_end.json")
        self.assertEqual(get_dates(obj_data, self.client), "1993")

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

    @override_settings(OFFSITE_BUILDINGS=["Armonk"])
    def test_get_locations(self):
        for fixture, expected in [("locations.json", "106.66.7"), ("locations_offsite.json", "Armonk.1.66.7")]:
            obj_data = json_from_fixture(fixture)
            self.assertEqual(get_locations(obj_data), expected)

    def test_get_instance_data(self):
        obj_data = json_from_fixture("digital_object_instance.json")
        expected_values = ("digital_object", "Digital Object: digital object", None, "http://google.com", "238475",
                           "/repositories/2/digital_objects/3367")
        self.assertEqual(get_instance_data([obj_data]), expected_values)

        obj_data = json_from_fixture("mixed_materials_instance.json")
        expected_values = ("mixed materials", "Box 2", "Folder 12",
                           "106.66.7",
                           "A12345", "/repositories/2/top_containers/191161")
        self.assertEqual(get_instance_data([obj_data]), expected_values)

    def test_get_preferred_format(self):
        obj_data = json_from_fixture("object_digital.json")
        expected_data = ("digital_object", "Digital Object: digital object, Digital Object: digital object 2",
                         None, "http://google.com, http://google2.com", "238475, 238476",
                         "/repositories/2/digital_objects/3367, /repositories/2/digital_objects/3368")
        self.assertEqual(get_preferred_format(obj_data), expected_data)

        obj_data = json_from_fixture("object_microform.json")
        expected_data = ("microform",
                         "Reel 1, Reel 2",
                         None,
                         "106.66.7, 106.66.8",
                         "A12345, A123456", "/repositories/2/top_containers/191157, /repositories/2/top_containers/191158")
        self.assertEqual(get_preferred_format(obj_data), expected_data)

        obj_data = json_from_fixture("object_mixed.json")
        expected_data = ("mixed materials",
                         "Box 1, Box 2",
                         "Folder 22, Folder 11-22",
                         "106.66.7, 106.66.8",
                         "A12345, A123456", "/repositories/2/top_containers/191157, /repositories/2/top_containers/191158")
        self.assertEqual(get_preferred_format(obj_data), expected_data)

        obj_data = json_from_fixture("object_no_instance.json")
        expected_data = (None, None, None, None, None, None)
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

    def test_get_rights_info(self):
        item = json_from_fixture("object_restricted_ancestor.json")
        info = get_rights_info(item, self.client)
        self.assertTrue(isinstance(info, tuple))
        self.assertEqual(info[0], "closed")
        self.assertEqual(info[1], "Ancestor Note")

    def test_get_rights_status(self):
        for fixture, status in [
                ("object_restricted_note.json", "closed"),
                ("object_restricted_note_conditional.json", "conditional"),
                ("object_restricted_note_open.json", "open"),
                ("object_restricted_note_long_open.json", "open"),
                ("object_restricted_note_longer_open.json", "open"),
                ("object_restricted_note_scholarly_open.json", "open"),
                ("object_restricted_rights_statement.json", "closed"),
                ("object_restricted_rights_statement_conditional.json", "conditional")]:
            item = json_from_fixture(fixture)
            self.assertEqual(get_rights_status(item, self.client), status)

    def test_get_rights_text(self):
        for fixture, status in [
                ("object_restricted_boolean.json", None),
                ("object_restricted_note.json", "Restricted - Open 2025"),
                ("object_restricted_note_conditional.json", "Access copy unavailable. Please contact an archivist."),
                ("object_restricted_note_open.json", "Open for research."),
                ("object_restricted_rights_statement.json", "Rights statement note."),
                ("object_restricted_rights_statement_conditional.json", None)]:
            item = json_from_fixture(fixture)
            self.assertEqual(get_rights_text(item, self.client), status)

    def test_get_size(self):
        for fixture, size in [
                ("instances_singular.json", "1 box"),
                ("instances_multiple.json", "2 boxes"),
                ("instances_plural.json", "3 folders")]:
            instance = json_from_fixture(fixture)
            self.assertEqual(get_size(instance), size)

        instance = json_from_fixture("instances_error.json")
        with self.assertRaises(Exception, msg="Error parsing instances"):
            get_size(instance)

    def test_get_title(self):
        for fixture, expected in [
                ({"title": "foo"}, "foo"),
                ({"display_string": "bar"}, "bar"),
                ({"title": "baz", "display_string": "foo"}, "baz"),
                ({"title": "bas", "level": "series", "component_id": "1"}, "bas, Series 1")]:
            result = get_parent_title(fixture)
            self.assertEqual(result, expected)

    def test_indicator_to_integer(self):
        for indicator, expected_parsed in [("23ab", 23), ("C", 2)]:
            parsed = indicator_to_integer(indicator)
            self.assertEqual(parsed, expected_parsed)

    @patch("asnake.client.web_client.ASnakeClient")
    def test_get_restricted_in_container(self, mock_client):
        for fixture, expected in [
                ("unrestricted_search.json", ""),
                ("restricted_search.json", "Folder 122A, Folder 117A.1, Folder 118A.1, Folder 121A.1, Folder 123A.1, Folder 119A, Folder 120A.1")]:
            mock_client.get.return_value.json.return_value = json_from_fixture(fixture)
            result = get_restricted_in_container("/repositories/2/top_container/1", mock_client)
            self.assertEqual(result, expected)

    @patch("asnake.client.web_client.ASnakeClient")
    def test_get_formatted_resource_id(self, mock_client):
        for fixture, expected in [
                ({"id_0": "FA123"}, "FA123"),
                ({"id_0": "FA123", "id_1": "001"}, "FA123:001"),
                ({"id_0": "FA123", "id_1": "001", "id_2": "A"}, "FA123:001:A"),
                ({"id_0": "FA123", "id_1": "001", "id_2": "A", "id_3": "dev"}, "FA123:001:A:dev")]:
            result = get_formatted_resource_id(fixture, mock_client)
            self.assertEqual(result, expected)

    # Test is commented out as the code is currently not used, and this allows us to shed a few configs
    # def test_aeon_client(self):
    #     baseurl = random_string(20)
    #     client = AeonAPIClient(baseurl)
    #     self.assertEqual(client.baseurl, baseurl)
    #     self.assertEqual(client.session.headers.get("X-AEON-API-KEY"), settings.AEON_API_KEY)


class TestRoutines(TestCase):

    @patch("process_request.routines.Processor.get_data")
    def test_parse_item(self, mock_get_data):
        item = json_from_fixture("as_data.json")
        mock_get_data.return_value = [item]

        # Ensure objects return correct messages
        for restrictions, text, submit, reason in [
                ("closed", "foo", False, "This item is currently unavailable for request. It will not be included in request. Reason: foo"),
                ("open", "bar", True, None),
                ("conditional", "foobar", True, "This item may be currently unavailable for request. It will be included in request. Reason: foobar")]:
            mock_get_data.return_value[0]["restrictions"] = restrictions
            mock_get_data.return_value[0]["restrictions_text"] = text
            parsed = Processor().parse_item(mock_get_data.return_value[0]["uri"], "https://dimes.rockarch.org")
            self.assertEqual(parsed["submit"], submit)
            self.assertEqual(parsed["submit_reason"], reason)

        # Ensure objects with attached digital objects return correct message
        for format, submit in [
                ("Digital", True), ("digital_object", False), ("Mixed materials", True), ("microfilm", True)]:
            mock_get_data.return_value[0]["preferred_instance"]["format"] = format
            parsed = Processor().parse_item(item["uri"], "https://dimes.rockarch.org")
            self.assertEqual(parsed["submit"], submit)

        # Ensure objects without instances return correct message
        mock_get_data.return_value[0]["preferred_instance"] = {"format": None, "container": None,
                                                               "subcontainer": None, "location": None, "barcode": None, "uri": None}
        parsed = Processor().parse_item(item["uri"], "https://dimes.rockarch.org")
        self.assertEqual(parsed["submit"], False)
        self.assertEqual(parsed["submit_reason"], "This item is currently unavailable for request. It will not be included in request. Reason: Required information about the physical container of this item is not available.")

        mock_get_data.return_value = []
        parsed = Processor().parse_item(item["uri"], "https://dimes.rockarch.org")
        self.assertEqual(parsed["submit"], False)
        self.assertEqual(parsed["submit_reason"], "This item is currently unavailable for request. It will not be included in request. Reason: This item cannot be found.")

    @patch("process_request.routines.Processor.get_data")
    def test_parse_batch(self, mock_get_data):
        item = json_from_fixture("as_data.json")
        mock_get_data.return_value = [item]

        # Ensure objects return correct messages
        for restrictions, text, submit, reason in [
                ("closed", "foo", False, "This item is currently unavailable for request. It will not be included in request. Reason: foo"),
                ("open", "bar", True, None),
                ("conditional", "foobar", True, "This item may be currently unavailable for request. It will be included in request. Reason: foobar")]:
            mock_get_data.return_value[0]["restrictions"] = restrictions
            mock_get_data.return_value[0]["restrictions_text"] = text
            parsed = Processor().parse_batch([mock_get_data.return_value[0]["uri"]], "https://dimes.rockarch.org")
            self.assertIsInstance(parsed, list)
            self.assertEqual(len(parsed), 1)
            item = parsed[0]
            self.assertIsInstance(item, dict)
            self.assertEqual(item["submit"], submit)
            self.assertEqual(item["submit_reason"], reason)

        # Ensure objects with attached digital objects return correct message
        for format, submit in [
                ("Digital", True), ("digital_object", False), ("Mixed materials", True), ("microfilm", True)]:
            mock_get_data.return_value[0]["preferred_instance"]["format"] = format
            item = Processor().parse_batch([item["uri"]], "https://dimes.rockarch.org")[0]
            self.assertEqual(item["submit"], submit)

        # Ensure objects without instances return correct message
        mock_get_data.return_value[0]["preferred_instance"] = {"format": None, "container": None,
                                                               "subcontainer": None, "location": None, "barcode": None, "uri": None}
        item = Processor().parse_batch([item["uri"]], "https://dimes.rockarch.org")[0]
        self.assertEqual(item["submit"], False)
        self.assertEqual(item["submit_reason"], "This item is currently unavailable for request. It will not be included in request. Reason: Required information about the physical container of this item is not available.")

        mock_get_data.return_value = []
        parsed = Processor().parse_batch([item["uri"]], "https://dimes.rockarch.org")[0]
        self.assertEqual(parsed["submit"], False)
        self.assertEqual(parsed["submit_reason"], "This item is currently unavailable for request. It will not be included in request. Reason: This item cannot be found.")

    @patch("process_request.routines.Processor.get_data")
    def test_deliver_email(self, mock_get_data):
        mock_get_data.return_value = [json_from_fixture("as_data.json")]
        object_list = [json_from_fixture("as_data.json")["uri"]]
        for to, subject in [
                ("test@example.com", "Subject"),
                (["foo@example.com", "bar@example.com"], None)]:
            expected_to = to if isinstance(to, list) else [to]
            emailed = Mailer().send_message(to, object_list, subject, "", "https://dimes.rockarch.org")
            self.assertEqual(emailed, "email sent to {}".format(", ".join(expected_to)))
            self.assertTrue(isinstance(mail.outbox[0].to, list))
            self.assertIsNot(mail.outbox[0].subject, None)
            self.assertNotIn("location", mail.outbox[0].body)
            self.assertNotIn("barcode", mail.outbox[0].body)

    @aspace_vcr.use_cassette("aspace_request.json")
    @override_settings(RESTRICTED_IN_CONTAINER=False)
    @patch("process_request.routines.get_resource_creators")
    def test_get_data(self, mock_creators):
        mock_creators.return_value = "Philanthropy Foundation"
        get_as_data = Processor().get_data(["/repositories/2/archival_objects/1134638"], "https://dimes.rockarch.org")
        self.assertTrue(isinstance(get_as_data, list))
        self.assertEqual(len(get_as_data), 1)

    @aspace_vcr.use_cassette("aspace_request.json")
    @patch("asnake.client.web_client.ASnakeClient.get")
    def test_invalid_get_data(self, mock_as_get):
        error_message = random_string(15)
        mock_as_get.return_value.status_code = 404
        mock_as_get.return_value.text = ''
        mock_as_get.return_value.json.return_value = {"error": error_message}
        with self.assertRaises(Exception, msg=error_message):
            Processor().get_data(["/repositories/2/archival_objects/1134638"], "https://dimes.rockarch.org")

    @patch("process_request.routines.Processor.get_data")
    def test_send_aeon_requests(self, mock_get_data):
        mock_get_data.return_value = [json_from_fixture("as_data.json")]

        data = {"scheduled_date": date.today().isoformat(), "items": random_list()}
        delivered = AeonRequester().get_request_data("readingroom", "https://dimes.rockarch.org", **data)
        self.assertTrue(isinstance(delivered, dict))
        self.assertIn("GroupingIdentifier", delivered)

        data["format"] = "jpeg"
        delivered = AeonRequester().get_request_data("duplication", "https://dimes.rockarch.org", **data)
        self.assertTrue(isinstance(delivered, dict))
        self.assertNotIn("GroupingIdentifier", delivered)

        request_type = "foo"
        with self.assertRaises(ValueError, msg="Unknown request type '{}', expected either 'readingroom' or 'duplication'".format(request_type)):
            AeonRequester().get_request_data(request_type, "https://dimes.rockarch.org", **data)


class TestViews(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    def assert_handles_routine(self, request_data, view_str, view):
        request = self.factory.post(
            reverse(view_str), request_data, format="json")
        response = view.as_view()(request)
        self.assertEqual(response.status_code, 200, "Response error: {}".format(response.data))
        self.assertEqual(len(response.data), 1)

    def assert_handles_exceptions(self, patched_fn, exception_text, view_str, view):
        patched_fn.side_effect = Exception(exception_text)
        request = self.factory.post(
            reverse(view_str), {"items": random_list()}, format="json")
        response = view.as_view()(request)
        self.assertEqual(
            response.status_code, 500, "Request did not return a 500 response")
        self.assertEqual(
            response.data["detail"], exception_text, "Exception string not in response")

    @patch("process_request.routines.Processor.get_data")
    def test_download_csv_view(self, mock_get_data):
        to_process = random_list()
        mock_get_data.return_value = [json_from_fixture("as_data.json") for n in range(len(to_process))]
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

        self.assert_handles_exceptions(
            mock_get_data, "foobar", "download-csv", DownloadCSVView)

    @patch("process_request.routines.Mailer.send_message")
    def test_send_email_request_view(self, mock_sent):
        mock_sent.return_value = "email sent"
        self.assert_handles_routine(
            {"items": random_list(), "to_address": "test@example.com", "subject": "DIMES list"},
            "deliver-email",
            MailerView)
        self.assert_handles_exceptions(
            mock_sent, "foobar", "deliver-email", MailerView)

    @patch("process_request.routines.Processor.parse_item")
    def test_parse_request_view(self, mock_parse):
        parsed = {"foo": "bar"}
        mock_parse.return_value = parsed
        self.assert_handles_routine(
            {"item": random_string()}, "parse-individual", ParseItemRequestView)
        self.assert_handles_exceptions(
            mock_parse, "bar", "parse-individual", ParseItemRequestView)

    @patch("process_request.routines.Processor.parse_batch")
    def test_parse_batch_view(self, mock_parse):
        parsed = [{"foo": "bar"}]
        mock_parse.return_value = parsed
        self.assert_handles_routine(
            {"item": [random_string()]}, "parse-batch", ParseBatchRequestView)
        self.assert_handles_exceptions(
            mock_parse, "bar", "parse-batch", ParseBatchRequestView)

    @patch("process_request.routines.AeonRequester.get_request_data")
    def test_deliver_readingroomrequest_view(self, mock_send):
        delivered = {"foo": "bar"}
        mock_send.return_value = delivered
        self.assert_handles_routine(
            {"items": delivered, "scheduled_date": date.today().isoformat()},
            "deliver-readingroom", DeliverReadingRoomRequestView)
        self.assert_handles_exceptions(
            mock_send, "bar", "deliver-readingroom", DeliverReadingRoomRequestView)

    @patch("process_request.routines.AeonRequester.get_request_data")
    def test_deliver_duplicationrequest_view(self, mock_send):
        delivered = {"foo": "bar"}
        mock_send.return_value = delivered
        self.assert_handles_routine(
            {"items": delivered, "format": "jpeg"},
            "deliver-duplication", DeliverDuplicationRequestView)
        self.assert_handles_exceptions(
            mock_send, "bar", "deliver-duplication", DeliverDuplicationRequestView)

    @aspace_vcr.use_cassette("aspace_request.json")
    def test_status_view(self):
        response = self.client.get("http://testserver{}".format(reverse("ping")))
        self.assertEqual(response.status_code, 200)

    @patch("process_request.views.resolve_ref_id")
    def test_linkresolver_view(self, mock_resolve):
        with aspace_vcr.use_cassette("aspace_request.json") as cass:
            mock_uri = "/objects/123"
            mock_refid = "12345abcdef"
            mock_resolve.return_value = mock_uri
            response = self.client.get(reverse('resolve-request'), {"ref_id": mock_refid})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, f"{settings.DIMES_BASEURL}{mock_uri}")
            mock_resolve.assert_called_with(settings.ARCHIVESSPACE["repo_id"], mock_refid, ANY)

            cass.rewind()
            response = self.client.get(reverse('resolve-request'))
            self.assertEqual(response.status_code, 500)
