from asnake.aspace import ASpace
from datetime import datetime
#from rapidfuzz import fuzz
from request_broker import settings


class Routine:
    """
    Base routine class which is inherited by all other routines.

    Provides default clients for ArchivesSpace.
    """

    def __init__(self):
        self.aspace = ASpace(baseurl = settings.ARCHIVESSPACE["baseurl"],
                             username = settings.ARCHIVESSPACE["username"],
                             password = settings.ARCHIVESSPACE["password"],
                             repository = settings.ARCHIVESSPACE["repo_id"])

class ProcessRequest(Routine):
        # TODO: main section where processing happens
        # Push requests to submitted or unsubmitted
        # If open and delivery formats, mark as submittable

        # TO DO: add code to read through the rights in order
        # 1. PREMIS rights statements first
        # 2. Conditions governing access notes
        # 3. Next closest conditions governing access notes (inherited)
    """
    Runs through the process of iterating through requests, getting json information,
    checking delivery formats, checking restrictrions, and adding items to lists.
    """
    def get_data(self, item):
        """Gets an archival object from ArchivesSpace.

        Args:
            item (str): An ArchivesSpace URI.

        Returns:
            obj: An ArchivesSpace Archival Object.
        """
        obj = self.aspace.client.get(item)
        return obj

    def get_note_text(note):
        # TODO: Cut down code to only include accessrestrict notes? Or call from
        # data helpers library?
        """Parses note content from different note types.
        Args:
            note (array): an ArchivesSpace note.

        Returns:
            list: a list containing note content.
        """
        def parse_subnote(subnote):
            """Parses note content from subnotes.

            Args:
                subnote (array): an ArchivesSpace subnote.

            Returns:
                list: a list containing subnote content.
            """
            if subnote["jsonmodel_type"] in [
                    "note_orderedlist", "note_index"]:
                content = subnote["items"]
            elif subnote["jsonmodel_type"] in ["note_chronology", "note_definedlist"]:
                content = []
                for k in subnote["items"]:
                    for i in k:
                        content += k.get(i) if isinstance(k.get(i),
                                                          list) else [k.get(i)]
            else:
                content = subnote["content"] if isinstance(
                    subnote["content"], list) else [subnote["content"]]
            return content

        if note["jsonmodel_type"] == "note_singlepart":
            content = note["content"]
        elif note["jsonmodel_type"] == "note_bibliography":
            data = []
            data += note["content"]
            data += note["items"]
            content = data
        elif note["jsonmodel_type"] == "note_index":
            data = []
            for item in note["items"]:
                data.append(item["value"])
            content = data
        else:
            subnote_content_list = list(parse_subnote(sn)
                                        for sn in note["subnotes"])
            content = [
                c for subnote_content in subnote_content_list for c in subnote_content]
        return content

    def text_in_note(note, query_string):
        """Performs fuzzy searching against note text.

        Args:
            note (JSONModelObject): an ArchivesSpace note object.
            query_string (str): a string to match against.

        Returns:
            bool: True if a match is found for `query_string`, False if no match is
                found.
        """
        CONFIDENCE_RATIO = 97
        """int: Minimum confidence ratio to match against."""
        note_content = GetRestrictions.get_note_text(note)
        ratio = fuzz.token_sort_ratio(
            " ".join([n.lower() for n in note_content]),
            query_string.lower(),
            score_cutoff=CONFIDENCE_RATIO)
        return bool(ratio)

    def indicates_restriction(rights_statement, restriction_acts):
        """Parses a rights statement to determine if it indicates a restriction.

        Args:
            rights_statement (JSONModelObject): an ArchivesSpace rights statement.

        Returns:
            bool: True if rights statement indicates a restriction, False if not.
        """
        def is_expired(date):
            today = datetime.now()
            date = date if date else datetime.strftime("%Y-%m-%d")
            return False if (
                datetime.strptime(date, "%Y-%m-%d") >= today) else True

        if is_expired(rights_statement.get("end_date")):
            return False
        for act in rights_statement.get("acts"):
            if (act.get("restriction")
                    in restriction_acts and not is_expired(act.get("end_date"))):
                return True
        return False

    def is_restricted(obj, query_string, restriction_acts):
        # TODO: Could be reworked to search for specific strings instead of
        # accepting input query strings. Need to figure out strings to query for.
        """Parses an archival object to determine if it is restricted.

        Iterates through notes, looking for a conditions governing access note
        which contains a particular set of strings.
        Also looks for associated rights statements which indicate object may be
        restricted.

        Args:
            obj (JSONModelObject): an ArchivesSpace archival_object.
            restriction_acts (list): a list of strings to match restriction act against.

        Returns:
            bool: True if archival object is restricted, False if not.
        """
        for note in obj["notes"]:
            if note["type"] == "accessrestrict":
                if GetRestrictions.text_in_note(note, query_string.lower()):
                    return True
        for rights_statement in obj["rights_statements"]:
            if GetRestrictions.indicates_restriction(rights_statement, restriction_acts):
                return True
        return False

    def inherit_restrictions(obj):
        """Iterates up from an archial object level to find the nearest restriction
        act or restriction note.

        Args:
            obj: An ArchivesSpace archival object.
        """
        # TODO: Add code to look up and inherit accessrestrict notes. Will need
        # to address resource records at some point.
        pass

    def check_formats(obj):
        """Parses instances and creates a list of instance types. Matches list against
        list of acceptable delivery formats. Acceptable formats include digital,
        microform, or mixed materials.

        Args:
            obj (JSONModelObject): an ArchivesSpace archival object.

        Returns:
            bool: True on any match with delivery formats. None on no match or instances.
        """
        if obj.instances:
            for instance in obj.instances:
                if instance.instance_type in DeliveryFormats.formats:
                    return True
                else:
                    return None
        else:
            return None

    def return_formats(obj):
        """Returns a list of acceptable delivery formats for an archival object.

        Args:
            obj: An ArchivesSpace archival object.

        Returns:
            list: list of instance objects that match delivery formats.
        """
        for instance in obj.instances:
            pass

    def run(self, object_list):
        """Runs the process request functions with proper conditionals. First get
        object, then check restrictions, then check if proper delivery formats exist,
        and then gets delivery format information. If the obj, fails a check, it
        gets added to a dict of unsubmitted materials with reason for failure,
        if it passes all, add it and corresponding delivery format info to a submission
        dictionary.

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
        #raise AttributeError
# if DeliveryFormats.check_formats:
# run necessary checks
# add object to submission list
        # pass
    # else:
# Add object to unsubmitted list
    # pass

class SendEmail(Routine):
    """Sends unsubmitted data to the endpoint for email creation.
    """
    pass

class SendRequest(Routine):
    """Sends submitted data to Aeon for transaction creation in Aeon.
    """
    pass

class SendSerializer(Routine):
    """Sends data to the proper to an endpoint for CSV creation of submission data.
    """
    pass
