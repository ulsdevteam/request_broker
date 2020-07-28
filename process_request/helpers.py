from datetime import datetime

from rapidfuzz import fuzz


def get_container_indicators(instances):
    """Takes ArchivesSpace archival object json data and returns all containers and indicators.

    args:
        instances (list): AS instance data that is a list of dicts

    returns:
        string: a string representation of all container display strings.
    """
    containers = []
    if instances:
        for instance in instances:
            if instance.get("instance_type") == "digital_object":
                containers.append("Digital Object: " + instance.get("digital_object").get("_resolved").get("title"))
            else:
                containers.append(instance.get("sub_container").get("top_container").get("_resolved").get("type").capitalize()
                + ' ' +
                instance.get("sub_container").get("top_container").get("_resolved").get("indicator"))
        return ", ".join(containers)
    else:
        return None


def get_collection_creator(resource):
    """Takes json for an archival object that has the _resolved parameter on resource::linked_agents. Iterates through linked_agents; if the role is creator, appends to list, and returns list as a string."""
    creators = []
    for linked_agent in resource.get("linked_agents"):
        if linked_agent.get("role") == "creator":
            creators.append(linked_agent.get("_resolved").get('display_name').get('sort_name'))
    return ",".join(creators)


def get_location(top_container_info):
    """Gets a human-readable location string for a top container

    Args:
        top_container_info (dict): json for a top container (with resolved container locations)

     Returns:
         string: all locations associated with the top container, separated by a comma.
     """
    locations = []
    for c in top_container_info.get("container_locations"):
        locations.append(c.get("_resolved").get("title"))
    return ",".join(locations)


def get_container_field(top_container_info, container_field):
    """Gets the value from a top container field

    Args:
        top_container_info (dict): json for a top container
        container_field (str): top container field

    Returns:
        string: value of the top container field
    """
    return(top_container_info.get(container_field))


def check_for_instance_type(archival_object, type_to_check):
    """Gets the index value of a specific instance type for an archival object

    Args:
        archival_object (dict): json for an archival object
        type_to_check (str): instance type to check against

    Returns:
        int: index of the matching instance type in the list of instances
    """
    list_of_instances = []
    for i in archival_object.get("instances"):
        instance_type = i.get("instance_type")
        list_of_instances.append(instance_type)
    if type_to_check in list_of_instances:
        return list_of_instances.index(type_to_check)


def get_dates(archival_object):
    """Gets the dates of an archival object or its closest ancestor with a date

        Args:
            archival_object (dict): json for an archival object (with resolved ancestors)

        Returns:
            string: all dates associated with an archival object or its closest ancestor, separated by a comma

    Takes json for an archival object that has the _resolved parameter on ancestors. Gets date expression for an item. Starts at item level, goes up until a date is found"""
    dates = []
    if archival_object.get("dates"):
        dates = [get_expression(d) for d in archival_object.get("dates")]
    else:
        for a in archival_object.get("ancestors"):
            if a.get("_resolved").get("dates"):
                dates = [get_expression(d) for d in a.get("_resolved").get("dates")]
    return ",".join(dates)


def get_expression(date):
    """Returns a date expression for a date object. Concatenates start and end dates if no date expression exists.

    Args:
        date (dict): an ArchivesSpace date

    Returns:
        string: date expression for the date object

    """
    try:
        expression = date["expression"]
    except KeyError:
        if date.get("end"):
            expression = "{0}-{1}".format(date["begin"], date["end"])
        else:
            expression = date["begin"]
    return expression


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
        if subnote.get("jsonmodel_type") in [
                "note_orderedlist", "note_index"]:
            content = subnote.get("items")
        elif subnote.get("jsonmodel_type") in ["note_chronology", "note_definedlist"]:
            content = []
            for k in subnote.get("items"):
                for i in k:
                    content += k.get(i) if isinstance(k.get(i),
                                                      list) else [k.get(i)]
        else:
            content = subnote.get("content") if isinstance(
                subnote.get("content"), list) else [subnote.get("content")]
        return content

    if note.get("jsonmodel_type") in ["note_singlepart", "note_langmaterial"]:
        content = note.get("content")
    elif note.get("jsonmodel_type") == "note_bibliography":
        data = []
        data += note.get("content")
        data += note.get("items")
        content = data
    elif note.get("jsonmodel_type") == "note_index":
        data = []
        for item in note.get("items"):
            data.append(item.get("value"))
        content = data
    else:
        subnote_content_list = list(parse_subnote(sn)
                                    for sn in note.get("subnotes"))
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
    for note in archival_object.get("notes"):
        if note.get("type") == "accessrestrict":
            if text_in_note(note, query_string.lower()):
                return True
    for rights_statement in archival_object.get("rights_statements"):
        if indicates_restriction(rights_statement, restriction_acts):
            return True
    return False
