import csv
from datetime import datetime

from django.http import StreamingHttpResponse
from django.shortcuts import redirect
from request_broker import settings
from asnake.aspace import ASpace
from rest_framework.response import Response
from rest_framework.views import APIView

from .helpers import resolve_ref_id
from .routines import AeonRequester, Mailer, Processor
from .serializers import LinkResolverSerializer

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
        baseurl = request.META.get("HTTP_ORIGIN", "http://localhost:3000")
        return Processor().parse_item(uri, baseurl)


class MailerView(BaseRequestView):
    """Delivers email messages containing data."""

    def get_response_data(self, request):
        object_list = request.data.get("items")
        to_address = request.data.get("email")
        subject = request.data.get("subject", "")
        message = request.data.get("message")
        baseurl = request.META.get("HTTP_ORIGIN", "http://localhost:3000")
        emailed = Mailer().send_message(to_address, object_list, subject, message, baseurl)
        return {"detail": emailed}


class DeliverReadingRoomRequestView(BaseRequestView):
    """Delivers a request for records to be delivered to the reading room."""

    def get_response_data(self, request):
        request_data = request.data
        baseurl = request.META.get("HTTP_ORIGIN", "http://localhost:3000")
        delivered = AeonRequester().get_request_data(
            "readingroom", baseurl, **request_data)
        return delivered


class DeliverDuplicationRequestView(BaseRequestView):
    """Delivers a request for records to be duplicated."""

    def get_response_data(self, request):
        request_data = request.data
        baseurl = request.META.get("HTTP_ORIGIN", "http://localhost:3000")
        delivered = AeonRequester().get_request_data(
            "duplication", baseurl, **request_data)
        return delivered


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
        fieldnames = [key for key, _ in settings.EXPORT_FIELDS]
        writer = csv.DictWriter(pseudo_buffer, fieldnames=fieldnames, extrasaction="ignore")
        yield writer.writerow(dict((fn, fn) for fn in writer.fieldnames))
        for row in items:
            yield writer.writerow(row)

    def post(self, request):
        """Streams a large CSV file."""
        try:
            submitted = request.data.get("items")
            baseurl = request.META.get("HTTP_ORIGIN", "http://localhost:3000")
            processor = Processor()
            fetched = processor.get_data(submitted, baseurl)
            response = StreamingHttpResponse(
                streaming_content=(self.iter_items(fetched, Echo())),
                content_type="text/csv",
            ) 
            filename = "dimes-{}.csv".format(datetime.now().isoformat())
            response["Content-Disposition"] = "attachment; filename={}".format(filename)
            return response
        except Exception as e:
            return Response({"detail": str(e)}, status=500)

class LinkResolverView(APIView):
    """Takes POST from Islandora. Resolves ASpace ID"""

    def get(self,request):

        aspace = ASpace(baseurl=settings.ARCHIVESSPACE["baseurl"], username=settings.ARCHIVESSPACE["username"], password=settings.ARCHIVESSPACE["password"], repository=settings.ARCHIVESSPACE["repo_id"])

        try:
          data = request.GET["ref_id"]
          ref_id = LinkResolverSerializer(data)
          host = settings.HOSTNAME
          repo = settings.ARCHIVESSPACE["repo_id"]
          uri = resolve_ref_id(repo, data, aspace.client)
 	  
          response = redirect("{}/objects/{}".format(host,uri))
          return response
        except Exception as e:
            return Response({"detail": str(e)}, status=500)

