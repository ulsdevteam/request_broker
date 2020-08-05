from datetime import datetime

from ordered_set import OrderedSet
from rapidfuzz import fuzz


def get_container_indicators(item_json):
    """Returns container indicator(s) for an archival object.

    Args:
        item_json (dict): ArchivesSpace archival object information that has
            resolved top containers and digital objects.

    Returns:
        string or None: A concatenated string containing the container type and
            container indicator, or digital object title.
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
    """Returns the file versions for an ArchivesSpace digital object.

    Args:
        digital_object (dict): Resolved json of an ArchivesSpace digital object.

    Returns:
        string: all file version uris associated with the digital object,
            separated by a comma.
    """
    return ", ".join([v.get("file_uri") for v in digital_object.get("file_versions")])


def get_locations(top_container_info):
    """Gets a human-readable location string for a top container

    Args:
        top_container_info (dict): json for a top container (with resolved container locations)

     Returns:
         string: all locations associated with the top container, separated by a comma.
    """
    locations = None
    if top_container_info.get("container_locations"):
        locations = ",".join([c.get("_resolved").get("title") for c in top_container_info.get("container_locations")])
    return locations


def prepare_values(values_list):
    """Process an iterable of lists.

    For each list in the initial iterable, removes None values, deduplicates and
    returns either a string of joined list items or  None.

    Args:
        values_list (iterable): an iterable in which each item is a list.

    Returns:
        values_list (tuple): processed values.
    """
    for n, item in enumerate(values_list):
        parsed = OrderedSet(filter(None, item))
        values_list[n] = None if len(parsed) == 0 else ", ".join(list(parsed))
    return tuple(values_list)


def get_instance_data(instance_list):
    """Returns a dictionary of selected instance information.

    Args:
        instance_list (list): A list of ArchivesSpace instance information with
            resolved top containers and digital objects.

    Returns:
        tuple: a tuple containing instance type, indicator, location, and
            barcode for the instance.
    """
    instance_types = []
    containers = []
    locations = []
    barcodes = []
    for instance in instance_list:
        if instance["instance_type"] == "digital_object":
            instance_types.append("digital_object")
            containers.append("Digital Object: {}".format(instance.get("digital_object").get("_resolved").get("title")))
            locations.append(get_file_versions(instance.get("digital_object").get("_resolved")))
            barcodes.append(instance.get("digital_object").get("_resolved").get("digital_object_id"))
        else:
            instance_types.append(instance["instance_type"])
            top_container = instance.get("sub_container").get("top_container").get("_resolved")
            containers.append("{} {}".format(top_container.get("type").capitalize(), top_container.get("indicator")))
            locations.append(get_locations(top_container))
            barcodes.append(top_container.get("barcode"))
    return prepare_values([instance_types, containers, locations, barcodes])


def get_preferred_format(item_json):
    """Returns information about the format preferred for delivery.

    Iterates over instances in an archival object and gets the preferred
    delivery format based on instance types. Prioritizes digital objects,
    then microform, and then returns anything if there is an instance.

    Args:
        item_json (dict): ArchivesSpace archival object information that has
            resolved top containers and digital objects.

    Returns:
        preferred (tuple): a tuple containing concatenated information of the
            preferred format retrieved by get_instance_data.
    """
    preferred = None, None, None, None
    if item_json.get("instances"):
        instances = item_json.get("instances")
        if "digital_object" in instances:
            preferred = get_instance_data([i for i in instances if i["instance_type"] == "digital_object"])
        elif "microform" in instances:
            preferred = get_instance_data([i for i in instances if i["instance_type"] == "microform"])
        else:
            preferred = get_instance_data([i for i in instances])
    return preferred


def get_preferred_rights(item_json):
    """Returns restriction information. Evaluates rights statements if they exist; if not, evaluated restrictions apply boolean and return conditions governing access text; if neither exist, evaluate note content (including ancestors) to determine if material is restricted.

        Args:
            item_json (dict): json for an archival object

        Returns:
    """
    if item_json.get("rights_statements"):
        # TODO: check that there's a "disseminate" act
        # TODO: check if the "disseminate" act is restricted or conditional
        # TODO: if restricted or conditional, get basis (NOT act) note text
        return "something"
    if item_json.get("restrictions_apply"):
        # TODO: return restricted to restrctions apply field
        # TODO: traverse conditions governing access to find note text indicating restriction + return restrictions text
        return "something else"
    else:
        # TODO: traverse conditions governing access to find note text indicating restriction
        # TODO: if a restriction is indicated, return restricted to restrctions apply field + return restrictions text
        return "another thing"


def get_rights_notes(item_json):
    """Gets the conditions governing access of an archival object if it indicates a restriction or its closest ancestor with conditions governing access that indicates a restriction
    .
        Args:
            item_json (dict): json for an archival object (with resolved ancestors)
        Returns:
            string: note content of a conditions governing access that indicates a restriction
    """
    restricted_words = ["closed", "restricted"]
    if "accessrestrict" in [note.get("type") for note in item_json.get("notes")]:
        for note in item_json.get("notes"):
            if note.get("type") == "accessrestrict" and note.get("publish"):
                if any(x in get_note_text(note).lower() for x in restricted_words):
                    return "Restricted: {}".format(get_note_text(note))
    else:
        for ancestor in item_json.get("ancestors"):
            if "accessrestrict" in [note.get("type") for note in ancestor.get("notes")]:
                for note in ancestor.get("notes"):
                    if note.get("type") == "accessrestrict" and note.get("publish"):
                        if any(x in get_note_text(note).lower() for x in restricted_words):
                            return "Restricted: {}".format(get_note_text(note))


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
    """Gets the dates of an archival object or its closest ancestor with a date.
        Args:
            archival_object (dict): json for an archival object (with resolved ancestors)
        Returns:
            string: all dates associated with an archival object or its closest ancestor, separated by a comma
    """
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
