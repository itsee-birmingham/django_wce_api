from django.db.models.signals import post_save

from .models import BaseModel


def get_subclasses(cls):
    result = [cls]
    classes_to_inspect = [cls]
    while classes_to_inspect:
        class_to_inspect = classes_to_inspect.pop()
        for subclass in class_to_inspect.__subclasses__():
            if subclass not in result:
                result.append(subclass)
                classes_to_inspect.append(subclass)
    return result


def increment_version(sender, instance, created, **kwargs):
    if created is True:
        version_number = 1
    else:
        version_number = instance.version_number
        try:
            version_number += 1
        except TypeError:
            version_number = 1  # just in case something got saved with null

    # we can't save in a post_save or we get stuck in a recursion nightmare
    # Lots of places online say disconnect and reconnect the signal around the
    # save call but that felt wrong to me so I am using update instead of save
    # which does not trigger the post_save signal
    sender.objects.filter(id=instance.id).update(version_number=version_number)


for subclass in get_subclasses(BaseModel):
    post_save.connect(increment_version, subclass)
