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

class DeliveryFormats:
    # TO DO: add code to check through an archival object's instances
    # Check for instances, prioritize digital objects
    # Preference for delivery formats:
    # 1. Digital
    # 2. Microfilm
    # 3. Mixed materials

    def check_instances(object):
        containers = {}
        if object.instances:
            for instance in object.instances:
                type = instance.instance_type
                if instance.sub_container:
                    ref = instance.sub_container.top_container.ref
                else:
                    ref = instance.digital_object.ref
                containers.update({type : ref})
            if 'digital_object' in containers:
                return containers['digital_object']
            elif 'microform' in containers:
                return containers['microform']
            elif 'mixed_materials' in containers:
                return containers['mixed_materials']
            else:
    # TO DO: Add code to add to unsubmitted list
                unsubmitted.append(object)
        else:
    # TO DO: Write add to unsubmitted list
            unsubmitted.append(object)
