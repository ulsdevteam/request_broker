from asnake.aspace import ASpace
from django.core.mail import send_mail
from request_broker import settings

from .clients import AeonAPIClient
from .helpers import (get_container_indicators, get_dates,
                      get_preferred_format, get_resource_creator,
                      get_rights_info)


class Processor(object):
    """
    Processes requests by getting json information, checking restrictions, and getting
    delivery formats.
    """

    def get_data(self, item):
        """Gets data about an archival object from ArchivesSpace.

        Args:
            item (str): An ArchivesSpace URI.

        Returns:
            obj (dict): A JSON representation of an ArchivesSpace Archival Object.
        """
        aspace = ASpace(baseurl=settings.ARCHIVESSPACE["baseurl"],
                        username=settings.ARCHIVESSPACE["username"],
                        password=settings.ARCHIVESSPACE["password"],
                        repository=settings.ARCHIVESSPACE["repo_id"])
        obj = aspace.client.get(item, params={"resolve": ["resource::linked_agents", "ancestors",
                                                          "top_container", "top_container::container_locations", "instances::digital_object"]})
        if obj.status_code == 200:
            item_json = obj.json()
            item_collection = item_json.get("ancestors")[-1].get("_resolved")
            aggregation = item_json.get("ancestors")[0].get("_resolved").get("display_string") if len(item_json.get("ancestors")) > 1 else None
            format, container, location, barcode = get_preferred_format(item_json)
            restrictions, restrictions_text = get_rights_info(item_json)
            return {
                "creator": get_resource_creator(item_collection),
                "restrictions": restrictions,
                "restrictions_text": restrictions_text,
                "collection_name": item_collection.get("title"),
                "aggregation": aggregation,
                "dates": get_dates(item_json),
                "resource_id": item_collection.get("id_0"),
                "title": item_json.get("display_string"),
                "ref": item_json.get("uri"),
                "containers": get_container_indicators(item_json),
                "preferred_format": format,
                "preferred_container": container,
                "preferred_location": location,
                "preferred_barcode": barcode,
            }
        else:
            raise Exception(obj.json()["error"])

    def is_restricted(self, obj):
        """Checks whether an object is restricted in ArchivesSpace.

        Args:
            obj (JSONModelObject): An ArchivesSpace archival object.

        Returns:
            bool (boolean): True on any match with restrictions_apply. None on no match.
        """
        pass

    def inherit_restrictions(self, obj):
        """Checks for restrictions on an ancestor of the current archival object.

        Args:
            obj (JSONModelObject): An ArchivesSpace archival object.

        Returns:
            restriction (str): String representation of a rights statement note or
            accessrestrict note that details why an item is restricted.
        """
        pass

    def process_email_request(self, object_list):
        """Processes email requests.

        Args:
            object_list (list): A list of AS archival object URIs.

        Returns:
            data (list): A list of dicts of objects.
        """
        processed = []
        for item in object_list:
            processed.append(self.get_data(item))
        return processed

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
        if item.get("restrictions").lower() in ["closed"]:
            submit = False
            reason = "Item is restricted: {}".format(item.get("restrictions_text"))
        elif item.get("preferred_format").lower() == "digital":
            submit = False
            reason = "This item is available online."
        return submit, reason

    def parse_items(self, object_list):
        """Parses requested items to determine which are submittable. Adds a
        `submit` and `submit_reason` attribute to each item.

        Args:
            object_list (list): A list of AS archival object URIs.

        Returns:
            object_list (list): A list of dicts containing parsed item information.
        """
        for item in object_list:
            data = self.get_data(item)
            submit, reason = self.is_submittable(data)
            data["submit"] = submit
            data["submit_reason"] = reason
        return object_list


class Mailer(object):
    """Email delivery class."""

    def send_message(self, to_address, object_list, subject=None):
        """Sends an email with request data to an email address or list of
        addresses.

        Args:
            to_address (str): email address to send email to.
            object_list (list): list of requested objects.
            subject (str): string to attach to the subject of the email.

        Returns:
            str: a string message that the emails were sent.
        """
        recipient_list = to_address if isinstance(to_address, list) else [to_address]
        subject = subject if subject else "My List from DIMES"
        message = self.format_items(object_list)
        # TODO: decide if we want to send html messages
        send_mail(
            subject,
            message,
            settings.EMAIL_DEFAULT_FROM,
            recipient_list,
            fail_silently=False)
        return "email sent to {}".format(", ".join(recipient_list))

    def format_items(self, object_list):
        """Converts dicts into strings and appends them to message body.

        Location and barcode are not appended to the message.

        Args:
            object_list (list): list of requested objects.

        Returns:
            message (str): a string respresentation of the converted dicts.
        """
        message = ""
        for obj in object_list:
            for k, v in obj.items():
                if k in settings.EXPORT_FIELDS:
                    message += "{}: {}\n".format(k, v)
            message += "\n"
        return message


class AeonRequester(object):
    """Creates transactions in Aeon by sending data to the Aeon API."""

    def __init__(self):
        self.client = AeonAPIClient(settings.AEON_BASEURL)

    def send_request(self, request_type, **kwargs):
        """Delivers request to Aeon.

        Args:
            request_type (str): string indicating whether the request is for the
            readingroom or duplication.

        Returns:
            dict: json response.

        Raise:
            ValueError: if request_type is not readingroom or duplicate.
            ValueError: if resp.status_code does not equal 200.
        """
        if request_type == "readingroom":
            data = self.prepare_reading_room_request(kwargs)
        elif request_type == "duplication":
            data = self.prepare_duplication_request(kwargs)
        else:
            raise Exception(
                "Unknown request type '{}', expected either 'readingroom' or 'duplication'".format(request_type))
        resp = self.client.post("url", json=data)
        if resp.status_code == 200:
            return resp.json()
        else:
            raise Exception(resp.json())

    def prepare_duplication_request(self, request_data):
        """Maps duplication request data to Aeon fields.

        Args:
            request_data (dict): data about user-submitted requests.

        Returns:
            dict: data mapped from request_data to Aeon duplication fields.
        """
        return {
            "RequestType": "Loan",
            "DocumentType": "Default",
            "GroupingIdentifier": "GroupingField",
            "ScheduledDate": request_data.get("scheduled_date"),
            "UserReview": "No",
            "Items": self.parse_items(request_data.get("items"))
        }

    def prepare_reading_room_request(self, request_data):
        """Maps reading room request data to Aeon fields.

        Args:
            request_data (dict): data about user-submitted requests.

        Returns:
            dict: data mapped from request_data to Aeon reading room fields.
        """
        return {
            "RequestType": "Copy",
            "DocumentType": "Default",
            "Format": request_data.get("format"),
            "GroupingIdentifier": "GroupingField",
            "SkipOrderEstimate": "Yes",
            "UserReview": "No",
            "Items": self.parse_items(request_data.get("items"))
        }

    def parse_items(self, items):
        """Assigns item data to Aeon request fields.

        Args:
            items (list): a list of items from a request.

        Returns:
            parsed (list): a list of dictionaries containing parsed item data.
        """
        parsed = []
        for i in items:
            parsed.append({
                "CallNumber": i["resource_id"],
                # TODO: GroupingField should be the container ref
                # "GroupingField": ,
                "ItemAuthor": i["creator"],
                # TODO: ItemCitation is the RefID (consider if this is still useful)
                # "ItemCitation": ,
                "ItemDate": i["dates"],
                "ItemInfo1": i["title"],
                # TODO: should this be restrictions or restrictions_text?
                "ItemInfo2": i["restrictions_text"],
                "ItemInfo3": i["ref"],
                # TODO: ItemInfo4 is description of materials to copy (duplication requests only)
                # "ItemInfo4": ,
                # TODO: ItemIssue is Subcontainer type2/indicator2 info
                # "ItemIssue": ,
                "ItemNumber": i["barcode"],
                "ItemSubtitle": i["aggregation"],
                "ItemTitle": i["collection_name"],
                "ItemVolume": i["preferred_container"],
                "Location": i["preferred_location"]
            })
        return parsed
