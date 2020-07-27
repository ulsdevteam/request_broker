from asnake.aspace import ASpace
from request_broker import settings

from .helpers import (check_for_instance_type, get_collection_creator,
                      get_container_info, get_dates, get_location)


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
        obj = aspace.client.get(item, params={"resolve": ["resource::linked_agents", "ancestors", "top_container", "top_container::container_locations"]})
        if obj.status_code == 200:
            as_data = {}
            item_json = obj.json()
            item_collection = item_json.get("ancestors")[-1].get("_resolved")
            as_data['creator'] = get_collection_creator(item_json)
            as_data['restrictions'] = "TK"
            as_data['restrictions_text'] = "TK"
            as_data['collection_name'] = item_collection.get("title")
            if len(item_json.get("ancestors")) > 1:
                as_data['aggregation'] = item_json.get("ancestors")[0].get("_resolved").get("display_string")
            else:
                as_data['aggregation'] = ""
            as_data['dates'] = get_dates(item_json)
            as_data['resource_id'] = item_collection.get("id_0")
            as_data['title'] = item_json.get("display_string")
            as_data['ref'] = item_json.get("uri")
            if check_for_instance_type(item_json, "digital_object"):
                as_data['container'] = ""
                as_data['barcode'] = ""
                as_data['location'] = ""
            else:
                if check_for_instance_type(item_json, "microform"):
                    instance = item_json.get("instances")[check_for_instance_type(item_json, "microform")]
                else:
                    instance = item_json.get("instances")[0]
                    top_container_info = instance.get("sub_container").get("top_container").get("_resolved")
                as_data['barcode'] = get_container_info(top_container_info, "barcode")
                as_data['location'] = get_location(top_container_info)
                as_data['container'] = "{} {}".format(get_container_info(top_container_info, "type").title(), get_container_info(top_container_info, "indicator"))
            print(as_data)
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
        for item in object_list:
            try:
                self.get_data(item)
                print('after get_data')
            except Exception as e:
                print(e)
            return 'test'

    def process_readingroom_request(self, object_list):
        """Processes reading room requests.

        Args:
            object_list (list): A list of AS archival object URIs.

        Returns:
            submitted (list): A list of dicts of submittable objects with corresponding most
                desirable delivery format.
            unsubmitted (list): A list of dicts of unsubmittable objects with corresponding
                reason of failure.
        """
        for item in object_list:
            try:
                self.get_data(item)
            except Exception as e:
                print(e)
            return 'test'

    def process_duplication_request(self, object_list):
        """Processes duplication requests.

        Args:
            object_list (list): A list of AS archival object URIs.

        Returns:
            submitted (list): A list of dicts of submittable objects with corresponding most
                desirable delivery format.
            unsubmitted (list): A list of dicts of unsubmittable objects with corresponding
                reason of failure.
        """
        for item in object_list:
            try:
                self.get_data(item)
                print('after get_data')
            except Exception as e:
                print(e)
            return 'test'


class DeliverEmail(object):
    """Sends an email with request data to an email address or list of addresses.
    """
    pass


class DeliverReadingRoomRequest(object):
    """Sends submitted data to Aeon for transaction creation in Aeon.
    """
    pass


class DeliverDuplicationRequest(object):
    """Sends submitted data for duplication request creation in Aeon.
    """
