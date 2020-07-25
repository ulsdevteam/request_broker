from asnake.aspace import ASpace
from django.core.mail import send_mail
from request_broker import settings


class ProcessRequest(object):
    # TODO: main section where processing happens
    # Push requests to submitted or unsubmitted
    # If open and delivery formats, mark as submittable
    # TO DO: add code to read through the rights in order
    # 1. PREMIS rights statements first
    # 2. Conditions governing access notes
    # 3. Next closest conditions governing access notes/rights statements (inherited)
    """
    Runs through the process of iterating through requests, getting json information,
    checking delivery formats, checking restrictrions, and adding items to lists.
    """

    def get_data(self, item):
        """Gets an archival object from ArchivesSpace.

        Args:
            item (str): An ArchivesSpace URI.

        Returns:
            obj (dict): A JSON representation of an ArchivesSpace Archival Object.
        """
        aspace = ASpace(baseurl=settings.ARCHIVESSPACE["baseurl"],
                        username=settings.ARCHIVESSPACE["username"],
                        password=settings.ARCHIVESSPACE["password"],
                        repository=settings.ARCHIVESSPACE["repo_id"])
        obj = aspace.client.get(item)
        if obj.status_code == 200:
            return obj.json()
        else:
            raise Exception(obj.json()["error"])

    def get_creator(self, resource):
        """Gets a resource and then gets the creator for the resource. Iterates
        over agents and gets creator information.

        Args:
            resource (JSONModelObject): an ArchivesSpace resource object.

        Returns:
            collection_title (str): a string representation of a collection title.
            creators (list): a list of strings representing creator names.
        """
        pass

    def get_agent_data(self, agent):
        """Gets ArchivesSpace agent data from an agent uri.

        Args:
            agent (JSONModelObject): an ArchivesSpace agent object.

        Returns:
            agent_name (str): Agent name for associated agent.
        """
        pass

    def is_restricted(self, obj):
        """Checks whether an object is restricted in ArchivesSpace.

        Args:
            obj (JSONModelObject): An ArchivesSpace archival object.

        Returns:
            bool (boolean): True on any match with restrictions_apply. None on no match.
        """
        pass

    def inherit_restrictions(self, obj):
        """Iterates up through an object's parents, including resource level,
            to find the nearest restriction act note or accessrestrict note. Parses accessrestrict
            notes for note content.

        Args:
            obj (JSONModelObject): An ArchivesSpace archival object.

        Returns:
            restriction (str): String representation of a rights statement note or
            accessrestrict note that details why an item is restricted.
        """
        pass

    def inherit_dates(self, obj):
        """Iterates up through an object's parents, including resource level,
            to find the nearest date object.

        Args:
            obj (JSONModelObject): An ArchivesSpace archival object.

        Returns:
            dates (str): a date expression.
        """
        pass

    def check_formats(self, obj, formats):
        """Parses instances for existing instance types. Matches each type against
            list of acceptable delivery formats. Returns instance information for
            for the most desirable delivery format.

        Args:
            obj (JSONModelObject): an ArchivesSpace archival object.
            formats (list): A list of strings of acceptable delivery formats.

        Returns:
            bool (boolean): False on no instances or if instance type is not in accepted formats.
            instance (dict): A dict of instance information for most desirable delivery format.
        """
        if obj.instances:
            for instance in obj.instances:
                if instance.instance_type in formats:
                    pass
                else:
                    False
        else:
            return False

    def create_instance_data(self, instance):
        """Constructs a dictionary of instance information and location data.
        Calls get_top_container.

        Args:
            instance (dict): ArchivesSpace instance information.

        Returns:
            instance_data (dict): a constructed dictionary of instance data.
                This will include barcode, container indicators, container type,
                and location information.
        """
        pass

    def get_top_container(self, container):
        """Retrieves and returns top container data from a top container url information.
            Calls get_location_information.

        Args:
            container (JSONModelObject): an ArchivesSpace top container object.

        Returns:
            container_data (dict): a dictionary of combined top_container and location
                information.
        """
        pass

    def get_location_information(self, location):
        """Retrieves and returns location information for an ArchivesSpace location.

        Args:
            location (JSONModelObject): an ArchivesSpace location object.

        Returns:
            location_data (str): a concatenated string of location information.
        """
        pass

    def create_readingroom_request(self, obj, instance_data, restriction, creators, collection_title, dates):
        """Constructs a request for reading room materials out of provided data.

        Args:
            obj (JSONModelObject): an ArchivesSpace object
            instance_data (dict): a dictionary containing instance and location information for
                most desirable delivery format.
            restriction (str): a string representation of a restriction note or accessrestrict
            note contents.
            creators (list): a list of strings including all creator names.
            collection_title (str): a string representation of a collection title.
            dates (str): a date expression.

        Returns:
            readingroom_request (dict): a JSON compliant request that validates against
            RAC requirements for Reading Room request data.
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

    def parse_items(self, object_list):
        """Parses items into two lists.

        Args:
            object_list (list): A list of AS archival object URIs.

        Returns:
            submittable (list): A list of dicts of submittable objects with corresponding most
                desirable delivery format.
            unsubmittable (list): A list of dicts of unsubmittable objects with corresponding
                reason of failure.
        """
        submittable = []
        unsubmittable = []
        for item in object_list:
            data = self.get_data(item)
            # TODO: what if there's a URL?
            if data.get("restriction") or not data.get("container"):
                unsubmittable.append(data)
            else:
                submittable.append(data)
        return submittable, unsubmittable


class DeliverEmail(object):
    """Email delivery class."""

    def send_message(self, to_address, object_list, subject=None):
        """Sends an email with request data to an email address or list of
        addresses.
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
        """
        message = ""
        for obj in object_list:
            for k, v in obj.items():
                if k in settings.EXPORT_FIELDS:
                    message += "{}: {}\n".format(k, v)
            message += "\n"
        return message


class DeliverReadingRoomRequest(object):
    """Sends submitted data to Aeon for transaction creation in Aeon.
    """
    pass


class DeliverDuplicationRequest(object):
    """Sends submitted data for duplication request creation in Aeon.
    """
