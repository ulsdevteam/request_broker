

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
    pass
    #def check_restrictions(self, object):
        #if data_helpers.is_restricted(object):
            #unsubmitted.append(object.title)
        #else:
            #pass

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
