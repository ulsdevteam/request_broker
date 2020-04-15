from .models import MachineUser, User
#from rac_aspace.data_helpers import indicates_restriction, is_restricted


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
    def check_instances(object):
        containers = {}
        if object.instances:
            for instance in object.instances:
                type = instance.instance_type
                try:
                    ref = instance.sub_container.top_container.ref
                except KeyError:
                    ref = instance.digital_object.ref
                containers.update({type : ref})
            if 'digital_object' in containers:
                return containers['digital_object']
            elif 'microform' in containers:
                return containers['microform']
            elif 'mixed materials' in containers:
                return containers['mixed materials']
            else:
                unsubmitted.append(object.title)
        else:
            unsubmitted.append(object.title)
