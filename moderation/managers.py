from django.db.models.manager import Manager
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist


class MetaClass(type):

    def __new__(cls, name, bases, attrs):
        return super(MetaClass, cls).__new__(cls, name, bases, attrs)


class ModerationObjectsManager(Manager):

    def __call__(self, base_manager, *args, **kwargs):
        return MetaClass(
            self.__class__.__name__,
            (self.__class__, base_manager),
            {'use_for_related_fields': True})

    def filter_moderated_objects(self, query_set):
        from models import ModeratedObject

        unmoderated_objects = ModeratedObject.objects.filter(
            content_type=ContentType.objects.get_for_model(query_set.model))\
            .filter(moderation_date__isnull=True).values_list('object_pk',
                                                               flat=True)

        return query_set.exclude(pk__in=unmoderated_objects)

    def exclude_objs_by_visibility_col(self, query_set):
        from moderation.models import MODERATION_STATUS_REJECTED

        kwargs = {}
        kwargs[self.moderator.visibility_column] =\
            bool(MODERATION_STATUS_REJECTED)

        return query_set.exclude(**kwargs)

    def get_query_set(self):
        query_set = super(ModerationObjectsManager, self).get_query_set()

        if self.moderator.visibility_column:
            return self.exclude_objs_by_visibility_col(query_set)

        return self.filter_moderated_objects(query_set)

    @property
    def moderator(self):
        from moderation import moderation

        return moderation.get_moderator(self.model)


class ModeratedObjectManager(Manager):

    def get_for_instance(self, instance):
        '''Returns ModeratedObject for given model instance'''
        return self.get(
            object_pk=instance.pk,
            content_type=ContentType.objects.get_for_model(instance.__class__))
