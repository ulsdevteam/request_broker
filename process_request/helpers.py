from ordered_set import OrderedSet
from rapidfuzz import fuzz

CONFIDENCE_RATIO = 97  # Minimum confidence ratio to match against.
OPEN_TEXT = "open"
CLOSED_TEXT = "restricted"


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
    """Gets a string representation of a location for an ArchivesSpace top container.

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
    """Creates a standardized tuple for each item in an instance list depending on
    the item's instance type.

    Args:
        instance_list (list): A list of ArchivesSpace instance information with
            resolved top containers and digital objects.

    Returns:
        tuple: a tuple containing instance type, indicator, location,
            container barcode or digital object id, and container/digital object
            ref for the instance.
    """
    instance_types = []
    containers = []
    locations = []
    barcodes = []
    refs = []
    for instance in instance_list:
        if instance["instance_type"] == "digital_object":
            instance_types.append("digital_object")
            containers.append("Digital Object: {}".format(instance.get("digital_object").get("_resolved").get("title")))
            locations.append(get_file_versions(instance.get("digital_object").get("_resolved")))
            barcodes.append(instance.get("digital_object").get("_resolved").get("digital_object_id"))
            refs.append(instance.get("digital_object").get("ref"))
            print(instance_types, containers, locations, barcodes, refs)
        else:
            instance_types.append(instance["instance_type"])
            top_container = instance.get("sub_container").get("top_container").get("_resolved")
            containers.append("{} {}".format(top_container.get("type").capitalize(), top_container.get("indicator")))
            locations.append(get_locations(top_container))
            barcodes.append(top_container.get("barcode"))
            refs.append(instance.get("sub_container").get("top_container").get("ref"))
    return prepare_values([instance_types, containers, locations, barcodes, refs])


def get_preferred_format(item_json):
    """Gets the instance data for the preferred delivery format of the current archival
    object.

    Prioritizes digital objects, then microform, and then returns anything if there
    is an instance.

    Args:
        item_json (dict): ArchivesSpace archival object information that has
            resolved top containers and digital objects.

    Returns:
        preferred (tuple): a tuple containing concatenated information of the
            preferred format retrieved by get_instance_data.
    """
    preferred = None, None, None, None, None
    if item_json.get("instances"):
        instances = item_json.get("instances")
        if any("digital_object" in obj for obj in instances):
            preferred = get_instance_data([i for i in instances if i["instance_type"] == "digital_object"])
        elif any(obj.get("instance_type") == "microform" for obj in instances):
            preferred = get_instance_data([i for i in instances if i["instance_type"] == "microform"])
        else:
            preferred = get_instance_data([i for i in instances])
    return preferred


def get_rights_info(item_json):
    """Gets rights status and text for an archival object.

    If no parseable rights status is available, it is assumed the item is open.

    Args:
        item_json (dict): json for an archival object

    Returns:
        status, text: A tuple containing the rights status and text. Status is
        one of "closed", "conditional" or "open". Text is either None or a string
        describing the restriction.
    """
    status = get_rights_status(item_json)
    if not status:
        for ancestor in item_json["ancestors"]:
            status = get_rights_status(ancestor["_resolved"])
            if status:
                break
    text = get_rights_text(item_json)
    if not text:
        for ancestor in item_json["ancestors"]:
            text = get_rights_text(ancestor["_resolved"])
            if text:
                break
    return status if status else "open", text


def get_rights_status(item_json):
    """Determines restrictions status for an archival object.

    Evaluates an object's `restrictions_apply` boolean field, rights statements
    and accessrestrict notes (in that order) to determine if restrictions have
    been explicitly set on the archival object. Returns None if restrictions
    cannot be parsed from those three sources.

    Args:
        item_json (dict): json for an archival object

    Returns:
        status: One of "closed", "conditional", "open", None
    """
    status = None
    if item_json.get("restrictions_apply"):
        status = "closed"
    elif item_json.get("rights_statements"):
        for stmnt in item_json["rights_statements"]:
            if any([act["restriction"].lower() == "disallow" for act in stmnt.get("acts", [])]):
                status = "closed"
            elif any([act["restriction"].lower() == "conditional" for act in stmnt.get("acts", [])]):
                status = "conditional"
    elif [n for n in item_json.get("notes", []) if n["type"] == "accessrestrict"]:
        notes = [n for n in item_json["notes"] if n["type"] == "accessrestrict"]
        if any([text_in_note(n, CLOSED_TEXT) for n in notes]):
            status = "closed"
        elif any([text_in_note(n, OPEN_TEXT) for n in notes]):
            status = "open"
        else:
            status = "conditional"
    return status


def get_rights_text(item_json):
    """Fetches text describing restrictions on an archival object.

    Args:
        item_json (dict): json for an archival object (with resolved ancestors)
    Returns:
        string: note content of a conditions governing access that indicates a restriction
    """
    text = None
    if [n for n in item_json.get("notes", []) if (n["type"] == "accessrestrict" and n["publish"])]:
        text = ", ".join(
            [", ".join(get_note_text(n)) for n in item_json["notes"] if (n["type"] == "accessrestrict" and n["publish"])])
    elif item_json.get("rights_statements"):
        string = ""
        for stmnt in item_json["rights_statements"]:
            for note in stmnt["notes"]:
                string += ", ".join(get_note_text(note))
        text = string if string else None
    return text


def get_resource_creator(resource):
    """Gets all creators of a resource record and concatenate them into a string
    separated by commas.

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
    """Gets the date expressions of an archival object or the date expressions of the
    object's closest ancestor with date information.

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
    """Gets a date expression for a date object. Concatenates start and end dates
    into a string if no date expression exists.

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

    Args:
        note (dict): an ArchivesSpace note.

    Returns:
        list: a list containing note content.
    """

    def parse_subnote(subnote):
        """Parses note content from subnotes.

        Args:
            subnote (dict): an ArchivesSpace subnote.

        Returns:
            list: a list containing subnote content.
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

    if note.get("jsonmodel_type") in [
            "note_singlepart", "note_langmaterial", "note_rights_statement",
            "note_rights_statement_act"]:
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

    Args:
        note (dict): an ArchivesSpace note.
        query_string (str): a string to match against.

    Returns:
        bool: True if a match is found for `query_string`, False if no match is
            found.
    """
    note_content = get_note_text(note)
    ratio = fuzz.partial_ratio(
        " ".join([n.lower() for n in note_content]),
        query_string.lower(),
        score_cutoff=CONFIDENCE_RATIO)
    return bool(ratio)
