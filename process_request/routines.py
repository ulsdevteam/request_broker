from .models import MachineUser, User


# adding pseudocode

class ProcessRequest(object):
    # Read through list of requested archival objects
    pass

class GetObject(object):
    # Gets archival object information from ArchivesSpace
    # TO DO: write connections to ArchivesSpace
    pass

class ProcessObject(object):
    # TO DO: main section where processing happens
    # Push requests to submitted or unsubmitted
    # If open and delivery formats, mark as submittable
    pass

class CheckRestrictions(object):
    # TO DO: add code to read through the rights in order
    # 1. PREMIS rights statements first
    # 2. Conditions governing access notes
    # 3. Next closest conditions governing access notes (inherited)
    pass

class DeliveryFormats(object):
    # TO DO: add code to check through an archival object's instances
    # Check for instances, prioritize digital objects
    # Preference for delivery formats:
    # 1. Digital
    # 2. Microfilm
    # 3. Mixed materials
    containers = []
    if object.instances:
        for instance in instances:
    # TO DO: Write code that grabs all instance types and then container for desired format.
            pass
    else:
    # TO DO: Write add to unsubmitted list
        pass
