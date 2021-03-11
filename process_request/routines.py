from asnake.aspace import ASpace
from django.core.mail import send_mail
from request_broker import settings

from .helpers import (get_container_indicators, get_dates,
                      get_preferred_format, get_resource_creators,
                      get_rights_info, get_size, get_url, list_chunks)


class Processor(object):
    """
    Processes requests by getting json information, checking restrictions, and getting
    delivery formats.
    """

    def get_data(self, uri_list, dimes_baseurl):
        """Gets data about an archival object from ArchivesSpace.

        Args:
            uri_list (list): A list of ArchivesSpace Archival Object URIs.
            dimes_baseurl (str): base URL for links to objects in DIMES

        Returns:
            data (list): A list containing JSON representations of ArchivesSpace
                         Archival Objects.
        """
        aspace = ASpace(baseurl=settings.ARCHIVESSPACE["baseurl"],
                        username=settings.ARCHIVESSPACE["username"],
                        password=settings.ARCHIVESSPACE["password"],
                        repository=settings.ARCHIVESSPACE["repo_id"])
        chunked_list = list_chunks([uri.split("/")[-1] for uri in uri_list], 25)
        data = []
        for chunk in chunked_list:
            objects = aspace.client.get("/repositories/{}/archival_objects".format(settings.ARCHIVESSPACE["repo_id"]),
                                        params={
                "id_set": chunk,
                "resolve": [
                    "resource::linked_agents", "ancestors",
                    "top_container", "top_container::container_locations",
                    "instances::digital_object"]})
            if objects.status_code == 200:
                for item_json in objects.json():
                    item_collection = item_json.get("ancestors")[-1].get("_resolved")
                    parent = item_json.get("ancestors")[0].get("_resolved").get("display_string") if len(item_json.get("ancestors")) > 1 else None
                    format, container, subcontainer, location, barcode, container_uri = get_preferred_format(item_json)
                    restrictions, restrictions_text = get_rights_info(item_json, aspace.client)
                    data.append({
                        "creators": get_resource_creators(item_collection),
                        "restrictions": restrictions,
                        "restrictions_text": restrictions_text,
                        "collection_name": item_collection.get("title"),
                        "parent": parent,
                        "dates": get_dates(item_json, aspace.client),
                        "resource_id": item_collection.get("id_0"),
                        "title": item_json.get("display_string"),
                        "uri": item_json["uri"],
                        "dimes_url": get_url(item_json, dimes_baseurl, aspace.client),
                        "containers": get_container_indicators(item_json),
                        "size": get_size(item_json["instances"]),
                        "preferred_instance": {
                            "format": format,
                            "container": container,
                            "subcontainer": subcontainer,
                            "location": location,
                            "barcode": barcode,
                            "uri": container_uri,
                        }
                    })
            else:
                raise Exception(objects.json()["error"])
        return data

    def is_submittable(self, item):
        """Determines if a request item is submittable.

        Args:
            item (dict): request item data.

        Returns:
            submit (bool): indicate if the request item is submittable or not.
            reason (str): if applicable, a human-readable explanation for why
                the request is not submittable.
        """
        submit = True
        reason = None
        if not any(value for value in item["preferred_instance"].values()):
            submit = False
            reason = "This item is currently unavailable for request. It will not be included in request. Reason: Required information about the physical container of this item is not available."
        elif item["restrictions"] == "closed":
            submit = False
            reason = "This item is currently unavailable for request. It will not be included in request. Reason: {}".format(item.get("restrictions_text"))
        elif "digital" in item["preferred_instance"]["format"].lower():
            submit = False
            reason = "This item is already available online. It will not be included in request."
        elif item["restrictions"] == "conditional":
            reason = "This item may be currently unavailable for request. It will be included in request. Reason: {}".format(item.get("restrictions_text"))
        return submit, reason

    def parse_item(self, uri, baseurl):
        """Parses requested items to determine which are submittable. Adds a
        `submit` and `submit_reason` attribute to each item.

        Args:
            uri (str): An AS archival object URI.
            baseurl (str): base URL for links to objects in DIMES

        Returns:
            parsed (dict): A dicts containing parsed item information.
        """
        data = self.get_data([uri], baseurl)[0]
        submit, reason = self.is_submittable(data)
        return {"uri": uri, "submit": submit, "submit_reason": reason}


class Mailer(object):
    """Email delivery class."""

    def send_message(self, email, object_list, subject, message, baseurl):
        """Sends an email with request data to an email address or list of
        addresses.

        Args:
            email (str): email address to send email to.
            object_list (list): list of URIs for requested objects.
            subject (str): string to attach to the subject of the email.
            message (str): message to prepend to the email body.
            baseurl (str): base URL to use for links to objects in DIMES.

        Returns:
            str: a string message that the emails were sent.
        """
        message = message + "\n\n" if message else ""
        recipient_list = email if isinstance(email, list) else [email]
        subject = subject if subject else "My List from DIMES"
        processor = Processor()
        fetched = processor.get_data(object_list, baseurl)
        message += self.format_items(fetched)
        send_mail(
            subject,
            message,
            settings.EMAIL_DEFAULT_FROM,
            recipient_list,
            fail_silently=False)
        return "email sent to {}".format(", ".join(recipient_list))

    def format_items(self, object_list):
        """Appends select keys to the message body unless their value is None.

        Args:
            object_list (list): list of requested objects.

        Returns:
            message (str): a string respresentation of the converted dicts.
        """
        message = ""
        for obj in object_list:
            for key, label in settings.EXPORT_FIELDS:
                if obj[key]:
                    concat_str = "{}: {} \n".format(label, obj[key]) if label else "{} \n".format(obj[key])
                    message += concat_str
            message += "\n"
        return message


class AeonRequester(object):
    """Creates transactions in Aeon by sending data to the Aeon API."""

    def __init__(self):
        self.request_defaults = {
            "AeonForm": "EADRequest",
            "DocumentType": "Default",
            "GroupingIdentifier": "GroupingField",
            "GroupingOption_ItemInfo1": "Concatenate",
            "GroupingOption_ItemDate": "Concatenate",
            "GroupingOption_ItemTitle": "FirstValue",
            "GroupingOption_ItemAuthor": "FirstValue",
            "GroupingOption_ItemSubtitle": "FirstValue",
            "GroupingOption_ItemVolume": "FirstValue",
            "GroupingOption_ItemIssue": "Concatenate",
            "GroupingOption_ItemInfo2": "Concatenate",
            "GroupingOption_CallNumber": "FirstValue",
            "GroupingOption_ItemInfo3": "FirstValue",
            "GroupingOption_ItemCitation": "FirstValue",
            "GroupingOption_ItemNumber": "FirstValue",
            "GroupingOption_Location": "FirstValue",
            "UserReview": "No",
            "SubmitButton": "Submit Request",
        }

    def get_request_data(self, request_type, baseurl, **kwargs):
        """Delivers request to Aeon.

        Args:
            request_type (str): string indicating whether the request is for the
            readingroom or duplication.

        Returns:
            dict: Request data.

        Raise:
            ValueError: if request_type is not readingroom or duplicate.
        """
        processor = Processor()
        fetched = processor.get_data(kwargs.get("items"), baseurl)
        if request_type == "readingroom":
            data = self.prepare_reading_room_request(fetched, kwargs)
        elif request_type == "duplication":
            data = self.prepare_duplication_request(fetched, kwargs)
        else:
            raise ValueError(
                "Unknown request type '{}', expected either 'readingroom' or 'duplication'".format(request_type))
        return data

    def prepare_reading_room_request(self, items, request_data):
        """Maps reading room request data to Aeon fields.

        Args:
            items (list): Resolved data about AS archival objects.
            request_data (dict): data about user-submitted requests.

        Returns:
            data: Submission data for Aeon.
        """
        reading_room_defaults = {
            "WebRequestForm": "DefaultRequest",
            "RequestType": "Loan",
            "ScheduledDate": request_data.get("scheduledDate"),
            "SpecialRequest": request_data.get("questions"),
        }
        request_data = self.parse_items(items)
        return dict(**self.request_defaults, **reading_room_defaults, **request_data)

    def prepare_duplication_request(self, items, request_data):
        """Maps duplication request data to Aeon fields.

        Args:
            items (list): Resolved data about AS archival objects.
            request_data (dict): data about user-submitted requests.

        Returns:
            data: Submission data for Aeon.
        """
        duplication_defaults = {
            "WebRequestForm": "PhotoduplicationRequest",
            "RequestType": "Copy",
            "Format": request_data.get("format"),
            "SpecialRequest": request_data.get("questions"),
            "SkipOrderEstimate": "Yes",
        }
        request_data = self.parse_items(items, request_data.get("description", ""))
        return dict(**self.request_defaults, **duplication_defaults, **request_data)

    def parse_items(self, items, description=""):
        """Assigns item data to Aeon request fields.

        Args:
            items (list): a list of items from a request.

        Returns:
            parsed (dict): a dictionary containing parsed item data.
        """
        parsed = {"Request": []}
        for i in items:
            request_prefix = i["uri"].split("/")[-1]
            parsed["Request"].append(request_prefix)
            parsed.update({
                "CallNumber_{}".format(request_prefix): i["resource_id"],
                "GroupingField_{}".format(request_prefix): i["preferred_instance"]["uri"],
                "ItemAuthor_{}".format(request_prefix): i["creators"],
                "ItemCitation_{}".format(request_prefix): i["uri"],
                "ItemDate_{}".format(request_prefix): i["dates"],
                "ItemInfo1_{}".format(request_prefix): i["title"],
                "ItemInfo2_{}".format(request_prefix): "" if i["restrictions"] == "open" else i["restrictions_text"],
                "ItemInfo3_{}".format(request_prefix): i["uri"],
                "ItemInfo4_{}".format(request_prefix): description,
                "ItemNumber_{}".format(request_prefix): i["preferred_instance"]["barcode"],
                "ItemSubtitle_{}".format(request_prefix): i["parent"],
                "ItemTitle_{}".format(request_prefix): i["collection_name"],
                "ItemVolume_{}".format(request_prefix): i["preferred_instance"]["container"],
                "ItemIssue_{}".format(request_prefix): i["preferred_instance"]["subcontainer"],
                "Location_{}".format(request_prefix): i["preferred_instance"]["location"]
            })
        return parsed
