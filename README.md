# qabel-register

Publicly accessible user directory service (**opt-in** of course)

## Installation

* Python ≥ 3.4 (3.4 untested)
* Postgresql ≥ 9.5 (9.4 could work as well)

```
$ virtualenv _venv
$ . _venv/bin/activate
$ pip install -r requirements.txt
```

## Running the tests

```
# Requires no DB configuration
$ py.test
...
=== lots passed in 2.71 seconds ===
```

## Running the server

* Requires the database to be initialized and running

```
$ python manage.py runserver
```

* Todo: provide uwsgi.ini or a script
* Todo: proper settings hierarchy base|testing|production
* Todo: Readme in standard Qabel layout