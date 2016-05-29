from django.db import transaction


class UpdateItem:
    def __init__(self, action, field, value):
        self.action = action
        self.field = field
        self.value = value

    def verification_required(self):
        return self.action == 'create'

    def execute(self, identity):
        from .models import Entry
        existing_entry = Entry.objects.filter(identity=identity, field=self.field, value=self.value)
        if self.action == 'delete':
            existing_entry.delete()
        elif self.action == 'create':
            if existing_entry.count():
                return
            entry = Entry(identity=identity, field=self.field, value=self.value)
            entry.save()
        else:
            raise ValueError('Invalid UpdateItem.action "%s"' % self.action)


class UpdateRequest:
    def __init__(self, identity, update_items):
        self.identity = identity
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
                item.execute(self.identity)
            if any(item.action == 'delete' for item in self.items):
                # If an entry was deleted the identity may be garbage
                self.identity.delete_if_garbage()
