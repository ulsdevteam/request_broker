from datetime import datetime
from rapidfuzz import fuzz

# adding pseudocode
unsubmitted = []


class ProcessRequest(object):
    # Read through list of requested archival objects
    pass


class GetObject(object):
    # Gets archival object information from ArchivesSpace
    # TO DO: write connections to ArchivesSpace
    pass


class GetRestrictions:
    # TO DO: main section where processing happens
    # Push requests to submitted or unsubmitted
    # If open and delivery formats, mark as submittable

    # TO DO: add code to read through the rights in order
    # 1. PREMIS rights statements first
    # 2. Conditions governing access notes
    # 3. Next closest conditions governing access notes (inherited)

    def get_note_text(note):
        """Parses note content from different note types.

        Args:
            note (JSONModelObject): an ArchivesSpace note object.

        Returns:
            list: a list containing note content.
        """
        def parse_subnote(subnote):
            """Parses note content from subnotes.

            Args:
                subnote (JSONModelObject): an ArchivesSpace subnote object.

            Returns:
                list: a list containing subnote content.
            """
            if subnote.jsonmodel_type in [
                    'note_orderedlist', 'note_index']:
                content = subnote.items
            elif subnote.jsonmodel_type in ['note_chronology', 'note_definedlist']:
                content = []
                for k in subnote.items:
                    for i in k:
                        content += k.get(i) if isinstance(k.get(i),
                                                          list) else [k.get(i)]
            else:
                content = subnote.content if isinstance(
                    subnote.content, list) else [subnote.content]
            return content

        if note.jsonmodel_type == "note_singlepart":
            content = note.content
        elif note.jsonmodel_type == 'note_bibliography':
            data = []
            data += note.content
            data += note.items
            content = data
        elif note.jsonmodel_type == "note_index":
            data = []
            for item in note.items:
                data.append(item.value)
            content = data
        else:
            subnote_content_list = list(parse_subnote(sn) for sn in note.subnotes)
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
        note_content = get_note_text(note)
        ratio = fuzz.token_sort_ratio(
            " ".join([n.lower() for n in note_content]),
            query_string.lower(),
            score_cutoff=CONFIDENCE_RATIO)
        return bool(ratio)

    def indicates_restriction(rights_statement):
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

        rights_json = rights_statement.json()
        if is_expired(rights_json.get("end_date")):
            return False
        for act in rights_json.get("acts"):
            if (act.get("restriction") in [
                    "disallow", "conditional"] and not is_expired(act.get("end_date"))):
                return True
        return False

    def is_restricted(object):
        """Parses an archival object to determine if it is restricted.

        Iterates through notes, looking for a conditions governing access note
        which contains a particular set of strings.
        Also looks for associated rights statements which indicate object may be
        restricted.

        Args:
            object (JSONModelObject): an ArchivesSpace archival_object.

        Returns:
            bool: True if archival object is restricted, False if not.
        """
        query_string = "materials are restricted"
        for note in object.notes:
            if note.type == 'accessrestrict':
                if text_in_note(note, query_string):
                    return True
        for rights_statement in object.rights_statements:
            if indicates_restriction(rights_statement):
                return True
        return False

    def inherit_restrictions(object):
        # TO DO: Add code to look up and inherit accessrestrict notes
        pass


class DeliveryFormats:

    formats = [
        "digital_object",
        "microform",
        "mixed materials"
    ]

    def check_formats(object):
        """Parses instances and creates a list of instance types. Matches list against
        list of acceptable delivery formats.

        Args:
            object (JSONModelObject): an ArchivesSpace archival object.

        Returns:
            bool: True on any match with delivery formats. None on no match or instances.
        """
        if object.instances:
            for instance in object.instances:
                if instance.instance_type in DeliveryFormats.formats:
                    return True
                else:
                    return None
        else:
            return None

    def return_formats(object):
        for instance in object.instances:
            pass
