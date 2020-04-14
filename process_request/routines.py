from .models import MachineUser, User


# adding pseudocode
unsubmitted = []

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
    containers = {}

    def check_instances(self):
        if object.instances:
            for instance in instances:
                type = instance.instance_type
                if instance.sub_container:
                    ref = instance.sub_container.top_container.ref
                else:
                    ref = instance.digital_object.ref
                containers.update({type : ref})
            if 'digital_object' in key.containers:
                return containers[key]
            elif 'microform' in key.containers:
                return containers[key]
            elif 'mixed materials' in key.containers:
                return containers[key]
            else:
    # TO DO: Add code to add to unsubmitted list
                unsubmitted.apend(object)
        else:
    # TO DO: Write add to unsubmitted list
            unsubmitted.apend(object)
