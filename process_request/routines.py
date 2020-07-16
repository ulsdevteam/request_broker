from asnake.aspace import ASpace
from request_broker import settings


class Routine:
    """
    Base routine class which is inherited by all other routines.

    Provides default clients for ArchivesSpace.
    """

    def __init__(self):
        self.aspace = ASpace(baseurl=settings.ARCHIVESSPACE["baseurl"],
                             username=settings.ARCHIVESSPACE["username"],
                             password=settings.ARCHIVESSPACE["password"],
                             repository=settings.ARCHIVESSPACE["repo_id"])


class ProcessRequest(Routine):
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

    def get_data(self, obj):
        """Gets an archival object from ArchivesSpace.

        Args:
            obj (str): An ArchivesSpace URI.

        Returns:
            obj (dict): A JSON representation of an ArchivesSpace Archival Object.
        """
        obj = self.aspace.client.get(item)
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

    def check_formats(self, obj, formats):
        """Parses instances and for existing instance types. Matches each type against
        list of acceptable delivery formats. Returns instance information.

        Args:
            obj (JSONModelObject): an ArchivesSpace archival object.
            formats (list): A list of strings of acceptable delivery formats.

        Returns:
            bool (boolean): False on no instances or if instance type is not in accepted formats.
            instance_list (list): A list of dicts containing JSON representations of each
            instance.
        """
        if obj.instances:
            for instance in obj.instances:
                if instance.instance_type in formats:
                    pass
                else:
                    False
        else:
            return False

    def get_instance_data(self, instance):
        """Returns container and location information for instance objects. Constructs
        a dictionary of instance information. Calls get_top_container.

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

    def create_readingroom_request(self, obj, instance_data, restriction):
        """Constructs a request for reading room materials out of provided data.

        Args:
            obj (JSONModelObject): an ArchivesSpace object
            instance_data (dict): a dictionary containing instance and location information.
            restriction (str): a string representation of a restriction note or accessrestrict
            note contents.
            creators (list): a list of strings including all creator names.

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
                data = self.get_data(item)
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

    def process_csv_request(self, object_list):
        """Processes requests for a CSV download.

        Args:
            object_list (list): A list of AS archival object URIs.

        Returns:
            A streaming CSV file
        """
        for item in object_list:
            try:
                self.get_data(item)
                print('after get_data')
            except Exception as e:
                print(e)
            return 'test'


class DeliverEmail(Routine):
    """Sends an email with request data to an email address or list of addresses.
    """
    pass


class DeliverReadingRoomRequest(Routine):
    """Sends submitted data to Aeon for transaction creation in Aeon.
    """
    pass


class DeliverDuplicationRequest(Routine):
    """Sends submitted data for duplication request creation in Aeon.
    """


class DeliverCSV(Routine):
    """Create a streaming csv file based on original request.
    """
    pass
