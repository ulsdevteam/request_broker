import csv
from datetime import datetime

from django.http import StreamingHttpResponse
from request_broker import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from .routines import AeonRequester, DeliverEmail, ProcessRequest


class ParseRequestView(APIView):
    """Parses requests into a submittable and unsubmittable list."""

    def post(self, request, format=None):
        try:
            object_list = request.data.get("items")
            parsed = ProcessRequest().parse_items(object_list)
            return Response({"items": parsed}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)


class ProcessEmailRequestView(APIView):
    """Processes data in preparation for sending an email."""

    def post(self, request):
        try:
            object_list = request.data.get("items")
            processed = ProcessRequest().process_email_request(object_list)
            return Response({"items": processed}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)


class DeliverEmailView(APIView):
    """Delivers email messages containing data."""

    def post(self, request):
        try:
            object_list = request.data.get("items")
            to_address = request.data.get("to_address")
            subject = request.data.get("subject")
            emailed = DeliverEmail().send_message(to_address, object_list, subject)
            return Response({"detail": emailed}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)


class DeliverReadingRoomRequestView(APIView):
    """Delivers a request for records to be delivered to the reading room."""

    def post(self, request):
        try:
            request_data = request.data
            delivered = AeonRequester().send_request(
                "readingroom", **request_data)
            return Response({"detail": delivered}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)


class DeliverDuplicationRequestView(APIView):
    """Delivers a request for records to be delivered to the reading room."""

    def post(self, request):
        try:
            request_data = request.data
            delivered = AeonRequester().send_request(
                "duplication", **request_data)
            return Response({"detail": delivered}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)


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
            processor = ProcessRequest()
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
