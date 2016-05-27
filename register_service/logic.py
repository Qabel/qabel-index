from django.db import transaction


class UpdateItem:
    def __init__(self, action, identity, field, value):
        self.action = action
        self.identity = identity
        self.field = field
        self.value = value

    def verification_required(self):
        return self.action == 'create'

    def execute(self):
        from .models import Entry, Identity
        identity, _ = Identity.objects.get_or_create(defaults=self.identity, **self.identity)
        existing_entry = Entry.objects.filter(identity=identity, field=self.field, value=self.value)
        if self.action == 'delete':
            existing_entry.delete()
            if not identity.entry_set.count():
                # Clean up the identity if this was the last entry referring to it.
                identity.delete()
        elif self.action == 'create':
            if existing_entry.count():
                return
            entry = Entry(identity=identity, field=self.field, value=self.value)
            entry.save()
        else:
            raise ValueError('Invalid UpdateItem.action "%s"' % self.action)


class UpdateRequest:
    def __init__(self, update_items):
        self.items = update_items

    def is_verification_complete(self):
        return not any(item.verification_required() for item in self.items)

    def start_verification(self, pending_verification_factory):
        if self.is_verification_complete():
            return
        # TODO

    def execute(self):
        assert self.is_verification_complete(), "Verification incomplete, execute() called: logic bug"

        with transaction.atomic():
            for item in self.items:
                item.execute()
