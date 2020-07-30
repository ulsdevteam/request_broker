from datetime import datetime

from rapidfuzz import fuzz


def get_container_indicators(item_json):
    """Takes ArchivesSpace JSON archival object data with resolved top containers and returns a container indicator.

    Args:
        item_json (dict): ArchivesSpace archival object information that has resolved top containers and digital objects.

    Returns:
        string: A concatenated string containing the container type and container indicator, or digital object title.
                Or None if no instances.
    """
    indicators = []
    if item_json.get("instances"):
        for i in item_json.get("instances"):
            if i.get("instance_type") == "digital_object":
                indicators.append("Digital Object: {}".format(i.get("digital_object").get("_resolved").get("title")))
            else:
                top_container = i.get("sub_container").get("top_container").get("_resolved")
                indicators.append("{} {}".format(top_container.get("type").capitalize(), top_container.get("indicator")))
        return ", ".join(indicators)
    else:
        return None


def get_file_versions(digital_object):
    """Takes ArchivesSpace digital object json and returns a file version.

    Args:
        digital_object (dict): Resolved json of an ArchivesSpace digital object.

    Returns:
        string: all file version uris associated with the digital object, separated by a comma.
    """
    versions = [v.get("file_uri") for v in digital_object.get("file_versions")]
    return ", ".join(versions)


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


def get_instance_data(instance, type):
    """Takes ArchivesSpace instance information and returns a dictionary of selected instance information.

    Args:
        instances (dict): ArchivesSpace instance information that has resolved top containers and digital objects.
        type (string): a string representation of an instance type.

    Returns:
        tuple: a tuple containing instance type, indicator, location, and barcode for the instance.
    """
    if type == "digital_object":
        instance_type = "digital_object"
        container = "Digital Object: {}".format(instance.get("digital_object").get("_resolved").get("title"))
        location = get_file_versions(instance.get("digital_object").get("_resolved"))
        barcode = instance.get("digital_object").get("_resolved").get("digital_object_id")
    else:
        instance_type = instance["instance_type"]
        top_container = instance.get("sub_container").get("top_container").get("_resolved")
        container = "{} {}".format(top_container.get("type").capitalize(), top_container.get("indicator"))
        if top_container.get("container_locations"):
            location = get_location(top_container)
        else:
            location = None
        if top_container.get("barcode"):
            barcode = top_container.get("barcode")
        else:
            barcode = None
    return instance_type, container, location, barcode


def get_preferred_format(item_json):
    """Iterates over instances in an archival object and gets the preferred delivery format based on instance
    types. Prioritizes digital objects, then microform, and then returns anything if there is an instance.

    Args:
        item_json (dict): ArchivesSpace archival object information that has resolved top containers and digital objects.

    Returns:
        preferred (tuple): a tuple containing concatenated information of the preferred format retrieved by get_instance_data.
    """
    if item_json.get("instances"):
        instances = item_json.get("instances")
        instance_types = [i["instance_type"] for i in instances]
        if "digital_object" in instance_types:
            data = [get_instance_data(i, i["instance_type"]) for i in instances if i["instance_type"] == "digital_object"]
        elif "microform" in instance_types:
            data = [get_instance_data(i, i["instance_type"]) for i in instances if i["instance_type"] == "microform"]
        else:
            data = [get_instance_data(i, i["instance_type"]) for i in instances]
        for x in data:
            preferred = (",".join([x[0] for x in data]),
                         ",".join([x[1] for x in data]),
                         ",".join([x[2] for x in data if x[2]]),
                         ",".join([x[3] for x in data if x[3]]))
    else:
        preferred = (None, None, None, None)
    return(preferred)


def get_collection_creator(resource):
    """Returns a list of creators for a resource record.

    Args:
        resource (dict): resource record data.

    Returns:
        creators (string): resource creators, separated by a comma.
    """
    creators = []
    if resource.get("linked_agents"):
        for linked_agent in resource.get("linked_agents"):
            if linked_agent.get("role") == "creator":
                creators.append(linked_agent.get("_resolved").get('display_name').get('sort_name'))
    return ",".join(creators)


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
