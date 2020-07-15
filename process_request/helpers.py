from datetime import datetime

from rapidfuzz import fuzz


def get_note_text(note):
    """Parses note content from different note types.

    :param dict: an ArchivesSpace note.

    :returns: a list containing note content.
    :rtype: list
    """
    def parse_subnote(subnote):
        """Parses note content from subnotes.

        :param dict: an ArchivesSpace subnote.

        :returns: a list containing subnote content.
        :rtype: list
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

    if note["jsonmodel_type"] in ["note_singlepart", "note_langmaterial"]:
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

    :param dict note: an ArchivesSpace note.
    :param str query_string: a string to match against.

    :returns: True if a match is found for `query_string`, False if no match is
            found.
    :rtype: bool
    """
    CONFIDENCE_RATIO = 97
    """int: Minimum confidence ratio to match against."""
    note_content = get_note_text(note)
    ratio = fuzz.token_sort_ratio(
        " ".join([n.lower() for n in note_content]),
        query_string.lower(),
        score_cutoff=CONFIDENCE_RATIO)
    return bool(ratio)


def indicates_restriction(rights_statement, restriction_acts):
    """Parses a rights statement to determine if it indicates a restriction.

    :param dict rights_statement: an ArchivesSpace rights statement.

    :returns: True if rights statement indicates a restriction, False if not.
    :rtype: bool
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


def is_restricted(archival_object, query_string, restriction_acts):
    """Parses an archival object to determine if it is restricted.

    Iterates through notes, looking for a conditions governing access note
    which contains a particular set of strings.
    Also looks for associated rights statements which indicate object may be
    restricted.

    :param dict archival_object: an ArchivesSpace archival_object.
    :param list restriction_acts: a list of strings to match restriction act against.

    :returns: True if archival object is restricted, False if not.
    :rtype: bool
    """
    for note in archival_object["notes"]:
        if note["type"] == "accessrestrict":
            if text_in_note(note, query_string.lower()):
                return True
    for rights_statement in archival_object["rights_statements"]:
        if indicates_restriction(rights_statement, restriction_acts):
            return True
    return False
