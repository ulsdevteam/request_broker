import csv
from datetime import datetime

from django.http import StreamingHttpResponse
from request_broker import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from .routines import AeonRequester, Mailer, Processor


class BaseRequestView(APIView):
    """Base view which handles POST requests returns the appropriate response.

    Requires children to implement a `get_response_data` method."""

    def post(self, request, format=None):
        try:
            data = self.get_response_data(request)
            return Response(data, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)


class ParseRequestView(BaseRequestView):
    """Parses an item to determine whether or not it is submittable."""

    def get_response_data(self, request):
        uri = request.data.get("item")
        return Processor().parse_item(uri)


class ProcessEmailRequestView(BaseRequestView):
    """Processes data in preparation for sending an email."""

    def get_response_data(self, request):
        object_list = request.data.get("items")
        processed = Processor().process_email_request(object_list)
        return {"items": processed}


class MailerView(BaseRequestView):
    """Delivers email messages containing data."""

    def get_response_data(self, request):
        object_list = request.data.get("items")
        to_address = request.data.get("email")
        subject = request.data.get("subject")
        message = request.data.get("message")
        emailed = Mailer().send_message(to_address, object_list, subject, message)
        return {"detail": emailed}


class DeliverReadingRoomRequestView(BaseRequestView):
    """Delivers a request for records to be delivered to the reading room."""

    def get_response_data(self, request):
        request_data = request.data
        delivered = AeonRequester().send_request(
            "readingroom", **request_data)
        return {"detail": delivered}


class DeliverDuplicationRequestView(BaseRequestView):
    """Delivers a request for records to be duplicated."""

    def get_response_data(self, request):
        request_data = request.data
        delivered = AeonRequester().send_request(
            "duplication", **request_data)
        return {"detail": delivered}


class Echo:
    """An object that implements just the write method of the file-like
    interface, returning the object instead of buffering. Used to stream
    downloads.
    """

    def write(self, value):
        return value


class DownloadCSVView(APIView):
    """Downloads a CSV file."""

    def iter_items(self, items, pseudo_buffer):
        """Returns an iterable containing the spreadsheet rows."""
        fieldnames = settings.EXPORT_FIELDS
        writer = csv.DictWriter(pseudo_buffer, fieldnames=fieldnames, extrasaction="ignore")
        yield writer.writerow(dict((fn, fn) for fn in writer.fieldnames))
        for row in items:
            yield writer.writerow(row)

    def post(self, request):
        """Streams a large CSV file."""
        try:
            submitted = request.data.get("items")
            processor = Processor()
            fetched = [processor.get_data(item) for item in submitted]
            response = StreamingHttpResponse(
                streaming_content=(self.iter_items(fetched, Echo())),
                content_type="text/csv",
            )
            filename = "dimes-{}.csv".format(datetime.now().isoformat())
            response["Content-Disposition"] = "attachment; filename={}".format(filename)
            return response
        except Exception as e:
            return Response({"detail": str(e)}, status=500)
