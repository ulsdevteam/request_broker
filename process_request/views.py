import csv
from datetime import datetime

from django.http import StreamingHttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from .routines import ProcessRequest


class ProcessRequestView(APIView):
    '''
    Calls the ProcessRequest class from routines.
    '''

    def post(self, request, format=None):
        object_list = request.data.get('items')
        process_list = ProcessRequest().process_readingroom_request(object_list)
        return Response(process_list, status=200)


class ProcessEmailRequestView(APIView):
    """Processes data in preparation for sending an email."""

    def post(self, request):
        try:
            object_list = request.data.get('items')
            process_list = ProcessRequest().process_email_request(object_list)
            return Response(process_list, status=200)
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
        fieldnames = ["creator", "collection_name", "aggregation", "dates",
                      "resource_id", "container", "title", "restrictions", "ref"]
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
