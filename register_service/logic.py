from django.db import transaction

import register_service


class UpdateItem:
    def __init__(self, action, field, value):
        self.action = action
        self.field = field
        self.value = value

    def verification_required(self, public_key_verified=False):
        return self.action == 'create' or not public_key_verified

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
    def __init__(self, identity, public_key_verified, update_items):
        self.identity = identity
        self.public_key_verified = public_key_verified
        self.items = update_items

    def is_verification_complete(self):
        return not any(item.verification_required(self.public_key_verified) for item in self.items)

    def start_verification(self, pending_verification_factory):
        if self.is_verification_complete():
            return
        vm = register_service.verification.VerificationManager(self.identity, self.public_key_verified,
                                                               pending_verification_factory)
        vm.start_verification(self.items)

    def execute(self):
        with transaction.atomic():
            for item in self.items:
                item.execute(self.identity)
            if any(item.action == 'delete' for item in self.items):
                # If an entry was deleted the identity may be garbage
                self.identity.delete_if_garbage()
