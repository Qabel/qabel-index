{% extends "mail_templated/base.tpl" %}

{% block subject %}
Qabel Directory - Please confirm request
{% endblock %}

{% block body %}
{# plain text #}

Dear Qabel user,

{% if action == 'create' %}
you (or someone else using your email) has requested to publicly link this email address, {{ email }}
to the following alias and public key:
{% else %}
you (or someone else using your email) has requested to remove this email address, {{ email }}
from the following alias and public key:
{% endif %}

# TODO standard pubkey/fingerprint format?

* Alias: {{ identity.alias }}
* Public key: {{ identity.public_key }}

Click the following link to confirm:

{{ confirm_url }}

If you wish to deny this request, click this link instead:

{{ deny_url }}
{% endblock %}

{% block html %}
# TODO
{% endblock %}