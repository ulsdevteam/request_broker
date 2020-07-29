from datetime import datetime

from rapidfuzz import fuzz


def get_container_indicators(instance):
    """Takes ArchivesSpace JSON instance data with resolved top containers and returns a container indicator.

    Args:
        instance (dict): ArchivesSpace instance information that has resolved top containers and digital objects.

    Returns:
        string: A concatenated string containing the container type and container indicator, or digital object title.
    """
    if instance.get("instance_type") == "digital_object":
        return "Digital Object:  {}".format(instance.get("digital_object").get("_resolved").get("title"))
    else:
        top_container = instance.get("sub_container").get("top_container").get("_resolved")
        return "{} {}".format(top_container.get("type").capitalize(), top_container.get("indicator"))


def get_file_versions(digital_object):
    """Takes ArchivesSpace digital object json and returns a file version.

    Args:
        digital_object (dict): Resolved json of an ArchivesSpace digital object.

    Returns:
        string: all file version uris associated with the digital object, separated by a comma.
    """
    versions = [v.get("file_uri")) for v in digital_object.get("file_versions")]
    return ", ".join(versions)


def get_instance_data(instance, type):
    """Takes ArchivesSpace instance information and returns a dictionary of selected instance information.

    Args:
        instance (dict): ArchivesSpace instance information that has resolved top containers and digital objects.
        type (string): a string representation of an instance type.

    Returns:
        instance_data (dict): returns a dict container instance type, indicator, location, and barcode for the instance.
    """
    instance_data = {}
    instance_data["instance_type"] = type
    instance_data["indicator"] = get_container_indicators(instance)
    if type == "digital_object":
        digital_object = instance.get("digital_object").get("_resolved")
        instance_data["location"] = get_file_versions(digital_object)
        instance_data["barcode"] = None
    else:
        top_container = instance.get("sub_container").get("top_container").get("_resolved")
        instance_data["location"] = get_location(top_container)
        instance_data["barcode"] = top_container.get("barcode")
    return instance_data


def get_preferred_format(instances):
    """Iterates over instances and gets the preferred delivery format based on delivery formats set in the settings.

    Args:
        instances (list): a list of ArchivesSpace instance dictionaries.

    Returns:
        preferred (list): a list of string instance information retrieved by get_instance_data.
    """
    instance_types = [i["instance_type"] for i in instances]
    if "digital_object" in instance_types:
        preferred = [get_instance_data(i, i["instance_type"]) for i in instances if i["instance_type"] == "digital_object"]
    elif "microform" in instance_types:
        preferred = [get_instance_data(i, i["instance_type"]) for i in instances if i["instance_type"] == "microform"]
    elif "microfilm" in instance_types:
        preferred = [get_instance_data(i, i["instance_type"]) for i in instances if i["instance_type"] == "microfilm"]
    elif "mixed materials" in instance_types:
        preferred = [get_instance_data(i, i["instance_type"]) for i in instances if i["instance_type"] == "mixed materials"]
    else:
        return None
    return preferred


def set_preferred_data(data, indicator=None, type=None, location=None):
    """Takes a dictionary and sets arguments to key, value pairs in that dictionary.

    Args:
        data (dict): the dictionary to write to.
        indicator (string): string representation of a container type and indicator
        type (string): string representation of an instance type
        location (string): string representation of a container's location

    Return:
        data (dict): returns an updated dictionary with new key, value pairs
    """
    data['preferred_container'] = indicator
    data['preferred_format'] = type
    data['preferred_location'] = location
    return data


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
    [locations.append(c.get("_resolved").get("title")) for c in top_container_info.get("container_locations")]
    return ",".join(locations)


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
