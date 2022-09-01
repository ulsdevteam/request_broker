import json
import re

import inflect
import shortuuid
from asnake.utils import (format_resource_id, get_date_display, get_note_text,
                          text_in_note)
from django.conf import settings
from ordered_set import OrderedSet

CONFIDENCE_RATIO = 97  # Minimum confidence ratio to match against.
OPEN_TEXT = ["Open for research", "Open for scholarly research"]
CLOSED_TEXT = ["Restricted"]


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

    Adds the building name for offsite locations only.

    Args:
        top_container_info (dict): json for a top container (with resolved container locations)

     Returns:
         string: all locations associated with the top container, separated by a comma.
    """

    def make_short_location(loc_data):
        location_list = [loc_data.get("room", "").strip().replace("Vault ", ""),
                         loc_data.get("coordinate_1_indicator", "").strip(),
                         loc_data.get("coordinate_2_indicator", "").strip()]
        if loc_data.get("building") in settings.OFFSITE_BUILDINGS:
            location_list.insert(0, loc_data["building"])
        return ".".join(location_list)

    locations = None
    if top_container_info.get("container_locations"):
        locations = ",".join([make_short_location(c["_resolved"]) for c in top_container_info.get("container_locations")])
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
    subcontainers = []
    locations = []
    barcodes = []
    refs = []
    for instance in instance_list:
        if instance["instance_type"] == "digital_object":
            instance_types.append("digital_object")
            resolved = instance.get("digital_object").get("_resolved")
            containers.append("Digital Object: {}".format(resolved.get("title")))
            locations.append(get_file_versions(resolved))
            barcodes.append(resolved.get("digital_object_id"))
            refs.append(resolved.get("uri"))
        else:
            instance_types.append(instance["instance_type"])
            sub_container = instance.get("sub_container")
            top_container = instance.get("sub_container").get("top_container").get("_resolved")
            containers.append("{} {}".format(top_container.get("type").capitalize(), top_container.get("indicator")))
            locations.append(get_locations(top_container))
            barcodes.append(top_container.get("barcode"))
            refs.append(top_container["uri"])
            if all(["type_2" in sub_container, "indicator_2" in sub_container]):
                subcontainers.append("{} {}".format(sub_container.get("type_2").capitalize(), sub_container.get("indicator_2")))
    return prepare_values([instance_types, containers, subcontainers, locations, barcodes, refs])


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
    preferred = None, None, None, None, None, None
    if item_json.get("instances"):
        instances = item_json.get("instances")
        if any("digital_object" in obj for obj in instances):
            preferred = get_instance_data([i for i in instances if i["instance_type"] == "digital_object"])
        elif any(obj.get("instance_type") == "microform" for obj in instances):
            preferred = get_instance_data([i for i in instances if i["instance_type"] == "microform"])
        else:
            preferred = get_instance_data([i for i in instances])
    return preferred


def get_restricted_in_container(container_uri, client):
    """Fetches information about other restricted items in the same container.

    Args:
        container_uri (string): A URI for an ArchivesSpace Top Container.

    Returns:
        restricted (string): a comma-separated list of other restricted items in
            the same container.
    """
    restricted = []
    this_page = 1
    more = True
    while more:
        escaped_url = container_uri.replace('/', '\\/')
        search_uri = f"repositories/{settings.ARCHIVESSPACE['repo_id']}/search?q=top_container_uri_u_sstr:{escaped_url}&page={this_page}&fields[]=uri,json,ancestors&resolve[]=ancestors:id&type[]=archival_object&page_size=25"
        items_in_container = client.get(search_uri).json()
        for item in items_in_container["results"]:
            item_json = json.loads(item["json"])
            status = get_rights_status(item_json, client)
            if not status:
                for ancestor_uri in item["_resolved_ancestors"]:
                    for ancestor in item["_resolved_ancestors"][ancestor_uri]:
                        status = get_rights_status(json.loads(ancestor["json"]), client)
                        if status:
                            break
            if status in ["closed", "conditional"]:
                for instance in item_json["instances"]:
                    sub_container = instance["sub_container"]
                    if all(["type_2" in sub_container, "indicator_2" in sub_container]):
                        restricted.append(f"{sub_container['type_2'].capitalize()} {sub_container['indicator_2']}")
        this_page += 1
        if this_page > items_in_container["last_page"]:
            more = False
    return ", ".join(restricted)


def get_rights_info(item_json, client):
    """Gets rights status and text for an archival object.

    If no parseable rights status is available, it is assumed the item is open.

    Args:
        item_json (dict): json for an archival object
        client: an ASnake client

    Returns:
        status, text: A tuple containing the rights status and text. Status is
        one of "closed", "conditional" or "open". Text is either None or a string
        describing the restriction.
    """
    status = get_rights_status(item_json, client)
    if not status:
        for ancestor in item_json["ancestors"]:
            status = get_rights_status(ancestor["_resolved"], client)
            if status:
                break
    text = get_rights_text(item_json, client)
    if not text:
        for ancestor in item_json["ancestors"]:
            text = get_rights_text(ancestor["_resolved"], client)
            if text:
                break
    return status if status else "open", text


def get_rights_status(item_json, client):
    """Determines restrictions status for an archival object.

    Evaluates an object's rights statements and accessrestrict notes (in that order)
    to determine if restrictions have been explicitly set on the archival object.
    Returns None if restrictions cannot be parsed from those three sources.

    Args:
        item_json (dict): json for an archival object
        client: an ASnake client

    Returns:
        status: One of "closed", "conditional", "open", None
    """
    status = None
    if item_json.get("rights_statements"):
        for stmnt in item_json["rights_statements"]:
            if any([act["restriction"].lower() == "disallow" for act in stmnt.get("acts", [])]):
                status = "closed"
            elif any([act["restriction"].lower() == "conditional" for act in stmnt.get("acts", [])]):
                status = "conditional"
    elif [n for n in item_json.get("notes", []) if n.get("type") == "accessrestrict"]:
        notes = [n for n in item_json["notes"] if n.get("type") == "accessrestrict"]
        if any([text_in_note(n, text, client, confidence=CONFIDENCE_RATIO) for text in CLOSED_TEXT for n in notes]):
            status = "closed"
            if any([text_in_note(n, text, client, confidence=CONFIDENCE_RATIO) for text in OPEN_TEXT for n in notes]):
                status = "open"
        elif any([text_in_note(n, text, client, confidence=CONFIDENCE_RATIO) for text in OPEN_TEXT for n in notes]):
            status = "open"
        else:
            status = "conditional"
    return status


def get_rights_text(item_json, client):
    """Fetches text describing restrictions on an archival object.

    Args:
        item_json (dict): json for an archival object (with resolved ancestors)
    Returns:
        string: note content of a conditions governing access that indicates a restriction
    """
    text = None
    if [n for n in item_json.get("notes", []) if (n.get("type") == "accessrestrict" and n["publish"])]:
        text = ", ".join(
            [", ".join(get_note_text(n, client)) for n in item_json["notes"] if (n.get("type") == "accessrestrict" and n["publish"])])
    elif item_json.get("rights_statements"):
        string = ""
        for stmnt in item_json["rights_statements"]:
            for note in stmnt["notes"]:
                string += ", ".join(note["content"])
        text = string if string else None
    return text


def get_resource_creators(resource, client):
    """Gets all creators of a resource record and concatenate them into a string
    separated by commas.

    Args:
        resource (dict): resource record data.

    Returns:
        creators (string): comma-separated list of resource creators.
    """
    creators = []
    if resource.get("linked_agents"):
        linked_agent_uris = [a["ref"].replace("/", "\\/") for a in resource["linked_agents"] if a["role"] == "creator"]
        search_uri = f"/repositories/{settings.ARCHIVESSPACE['repo_id']}/search?fields[]=title&type[]=agent_person&type[]=agent_corporate_entity&type[]=agent_family&page=1&q={' OR '.join(linked_agent_uris)}"
        resp = client.get(search_uri)
        resp.raise_for_status()
        creators = resp.json()["results"]
    return ", ".join([a["title"] for a in creators])


def get_dates(archival_object, client):
    """Gets human-readable dates of an archival object.

        Args:
            archival_object (dict): json for an archival object

        Returns:
            string: all dates associated with an archival object, separated by a comma
    """
    dates = [get_date_display(d, client) for d in archival_object.get("dates", [])]
    return ", ".join(dates) if len(dates) else None


def get_size(instances):
    """Attempts to parse extents from instances.

    Initially, child subcontainers are parsed to determine
    the extent number and extent type. If a child subcontainer does not
    exist, the parent container is parsed.
    """

    def append_to_list(extents, extent_type, extent_number):
        """Merges or appends extent objects to an extent list.

        Only operates over instances with a sub_container (i.e. skips
        digital object instances).

        Args:
            extents (list): a list of extents to update.
            extent_type (str): the extent type to add.
            extent_number (int): the extent number to add
        """
        matching_extents = [e for e in extents if e["extent_type"] == extent_type]
        if matching_extents:
            matching_extents[0]["number"] += extent_number
        else:
            extents.append({"extent_type": extent_type, "number": extent_number})
        return extents

    extents = []
    for instance in [i for i in instances if i.get("sub_container")]:
        try:
            sub_container_parseable = all(i_type in instance.get("sub_container", {}) for i_type in ["indicator_2", "type_2"])
            if sub_container_parseable:
                number_list = [i.strip() for i in instance["sub_container"]["indicator_2"].split("-")]
                range = sorted(map(indicator_to_integer, number_list))
                extent_type = instance["sub_container"]["type_2"]
                extent_number = range[-1] - range[0] + 1 if len(range) > 1 else 1
            else:
                instance_type = instance["instance_type"].lower()
                sub_container_type = instance["sub_container"]["top_container"]["_resolved"].get("type", "").lower()
                extent_type = "{} {}".format(instance_type, sub_container_type) if sub_container_type != "box" else sub_container_type
                extent_number = 1
            extents = append_to_list(extents, extent_type.strip(), extent_number)
        except Exception as e:
            raise Exception("Error parsing instances") from e
    return ", ".join(
        ["{} {}".format(
            e["number"], inflect.engine().plural(e["extent_type"], e["number"])) for e in extents])


def get_parent_title(obj_json):
    """Returns the title for an object's parent component.

    If a component identifier is present, appends that identifier plus the
    object's level.
    """
    title = obj_json.get("title", obj_json.get("display_string")).strip()
    if obj_json.get("component_id"):
        title = "{}, {} {}".format(title, obj_json["level"].capitalize(), obj_json["component_id"])
    return title


def get_url(obj_json, host, client):
    """Returns a full URL for an object."""
    uuid = shortuuid.uuid(name=obj_json["uri"])
    return "{}/collections/{}".format(host, uuid) if has_children(obj_json, client) else "{}/objects/{}".format(host, uuid)


def has_children(obj_json, client):
    """Checks whether an archival object has children using the tree/node endpoint."""
    resource_uri = obj_json['resource']['ref']
    tree_node = client.get('{}/tree/node?node_uri={}'.format(resource_uri, obj_json['uri'])).json()
    return True if tree_node['child_count'] > 0 else False


def indicator_to_integer(indicator):
    """Converts an instance indicator to an integer.

    An indicator can be an integer (23) a combination of integers and letters (23b)
    or just a letter (B).
    """
    try:
        integer = int(indicator)
    except ValueError:
        parsed = re.sub("[^0-9]", "", indicator)
        if len(parsed):
            return indicator_to_integer(parsed)
        integer = ord(indicator.lower()) - 97
    return integer


def list_chunks(lst, n):
    """Yield successive n-sized chunks from list.
    Args:
        lst (list): list to chunkify
        n (integer): size of chunk to produce
    """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def identifier_from_uri(uri):
    """Creates a short UUID.

    Uses `shortuuid`, which first creates a v5 UUID using an object's AS URI as
    a name, and then converts them to base57 using lowercase and uppercase
    letters and digits, and removing similar-looking characters such as
    l, 1, I, O and 0.

    This is a one-way process; while it is possible to consistently generate a
    given UUID given an AS URI, it is not possible to decode the URI from the
    UUID.

    Helper method copied from https://github.com/ulsdevteam/pisces/blob/base/fetcher/helpers.py#L81
    """
    return shortuuid.uuid(name=uri)


def resolve_ref_id(repo_id, ref_id, client):
    """ Accepts options to find archival objects using find_by_id method.

    Generates and returns a DIMES id from an ArchiveSpace URI.
    """
    aspace_objs = client.get('/repositories/{}/find_by_id/archival_objects?ref_id[]={}'.format(repo_id, ref_id)).json()
    aspace_obj = aspace_objs['archival_objects'][0]['ref']
    resolved = identifier_from_uri(aspace_obj)
    return resolved


def get_formatted_resource_id(resource, client):
    """Gets a formatted resource id from the resource

    Concatenates the resource id parts using the separator from the config
    """
    return format_resource_id(resource, client, settings.RESOURCE_ID_SEPARATOR)
