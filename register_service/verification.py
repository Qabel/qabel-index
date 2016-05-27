
"""

.. note::

    Validation => to check whether data matches the data model

    Verification => an action the user needs to complete to confirm a request


Hidden assumption for verification: some way or another we receive a HTTP request when the outcome is established.
E.g. link in a verification e-mail is clicked, SMS verification service POSTs to a specified URL, ...

TODO: define top-level interface (factory<update request|item, pending_verification_factory> ?)
"""


class EmailVerification:
    def __init__(self, identity, email):
        self.identity = identity
        self.email = email


class PhoneNumberVerification:
    def __init__(self, identity, phone):
        self.identity = identity
        self.phone = phone
