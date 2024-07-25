# Argus API Client

This is the official Python client library for the 
[Argus](https://github.com/Uninett/Argus) API server.

The Argus server is an incident registry, capable of aggregating alerts from 
multiple source systems. Argus also can send event notifications (via e-mail,
SMS, etc.) when incidents are created or resolved.

## Usage examples

The pyargus library models [the official API endoints of
Argus](https://argus-server.readthedocs.io/en/latest/api.html) as methods on an
API client object.

At the moment, only the methods and models needed to interact with
incident-related endpoints are supported.

The `Client` class is found in `pyargus.client`, and the various supported data
models, such as `Incident`, `Event`, `Acknowledgement` and `SourceSystem`, are
implemented in `pyargus.models`.

### Listing open incidents that have not been acknowledged

```pycon
>>> from pyargus.client import Client
>>> c = Client(api_root_url="https://argus.example.org/api/v2", token="foobar")
>>> for incident in c.get_incidents(open=True, acked=False):
...    print(incident)
...
Incident(pk=4, start_time=datetime.datetime(2021, 4, 4, 16, 37, 43, 293726, tzinfo=datetime.timezone(datetime.timedelta(seconds=7200), '+02:00')), end_time=datetime.datetime(9999, 12, 31, 23, 59, 59, 999999), source=SourceSystem(pk=2, name='testnav', type='nav', user=3, base_url='http://localhost/'), source_incident_id='202430', details_url='http://localhost/search/event/202430', description='uninett-gsw2 BGP session with 158.38.3.112 is DOWN', level=5, ticket_url='', tags={'location': 'Teknobyen Innovasjonssenter', 'kundetjeneste': 'Nett_CNaaS', 'kunde': 'example.org', 'event_type': 'bgpState', 'alert_type': 'bgpDown', 'room': '100', 'organization': 'uninett.srv', 'host': 'uninett-gsw2.uninett.no'}, stateful=True, open=True, acked=False)
Incident(pk=3, start_time=datetime.datetime(2021, 4, 4, 16, 32, 53, 128780, tzinfo=datetime.timezone(datetime.timedelta(seconds=7200), '+02:00')), end_time=datetime.datetime(9999, 12, 31, 23, 59, 59, 999999), source=SourceSystem(pk=2, name='testnav', type='nav', user=3, base_url='http://localhost/'), source_incident_id='202429', details_url='http://localhost/search/event/202429', description='uninett-gsw1 BGP session with 158.38.3.112 is DOWN', level=5, ticket_url='', tags={'location': 'Teknobyen Innovasjonssenter', 'kundetjeneste': 'Nett_CNaaS', 'kunde': 'example.org', 'event_type': 'bgpState', 'alert_type': 'bgpDown', 'host': 'uninett-gsw1.uninett.no', 'room': '100', 'organization': 'uninett.srv'}, stateful=True, open=True, acked=False)
Incident(pk=2, start_time=datetime.datetime(2017, 8, 31, 14, 58, 31, 118794, tzinfo=datetime.timezone(datetime.timedelta(seconds=7200), '+02:00')), end_time=datetime.datetime(9999, 12, 31, 23, 59, 59, 999999), source=SourceSystem(pk=2, name='testnav', type='nav', user=3, base_url='http://localhost/'), source_incident_id='184296', details_url='http://localhost/search/event/184296', description='Link DOWN on Gi0/3 at oldsmobile.lab (Simple is better than complex)', level=5, ticket_url='', tags={'room': '113', 'location': 'Teknobyen Innovasjonssenter', 'organization': 'uninett.testlab', 'kundetjeneste': 'Nett_CNaaS', 'kunde': 'example.org', 'event_type': 'linkState', 'alert_type': 'linkDown', 'host': 'oldsmobile.lab.uninett.no', 'interface': 'Gi0/3'}, stateful=True, open=True, acked=False)
```

As you can see, the arguments given to `get_incidents()` are translated
verbatim into the arguments supported by the `/incidents` endpoint in the API.

### List only "my" incidents

The incidents API also has an `/incidents/mine` endpoint, which works just like
the `/incidents` endpoint, but searches only the incidents that were posted
by the connecting user. This is useful for glue services, when they need to
compare the list of open Argus incidents it has produced with the current list
of active alerts in its source system.

Example:

```pycon
>>> from pyargus.client import Client
>>> c = Client(api_root_url="https://argus.example.org/api/v2", token="foobar")
>>> for incident in c.get_my_incidents(open=True, acked=False):
...    print(incident)
...
Incident(pk=3, start_time=datetime.datetime(2021, 4, 4, 16, 32, 53, 128780, tzinfo=datetime.timezone(datetime.timedelta(seconds=7200), '+02:00')), end_time=datetime.datetime(9999, 12, 31, 23, 59, 59, 999999), source=SourceSystem(pk=3, name='foobar, type='nav', user=4, base_url='http://localhost/'), source_incident_id='2716057', details_url='http://localhost/search/event/2716057', description='uninett-gsw1 BGP session with 158.38.3.112 is DOWN', level=5, ticket_url='', tags={'location': 'Teknobyen Innovasjonssenter', 'kundetjeneste': 'Nett_CNaaS', 'kunde': 'example.org', 'event_type': 'bgpState', 'alert_type': 'bgpDown', 'host': 'uninett-gsw1.uninett.no', 'room': '100', 'organization': 'uninett.srv'}, stateful=True, open=True, acked=False)
```

### Post a new incident

```pycon
>>> from pyargus.client import Client
>>> from pyargus.models import Incident
>>> from datetime import datetime
>>> c = Client(api_root_url="https://argus.example.org/api/v2", token="foobar")
>>> i = Incident(
...     description="The earth was demolished to make way for a hyperspace bypass", 
...     start_time=datetime.now(),
...     tags={
...         "host": "earth.example.org",
...     }
... )
>>> c.post_incident(i)
Incident(pk=8, start_time=datetime.datetime(2021, 4, 22, 11, 41, 53, 580947, tzinfo=datetime.timezone(datetime.timedelta(seconds=7200), '+02:00')), end_time=None, source=SourceSystem(pk=2, name='testnav', type='nav', user=3, base_url='http://localhost/'), source_incident_id='', details_url='', description='The earth was demolished to make way for a hyperspace bypass', level=5, ticket_url='', tags={'host': 'earth.example.org'}, stateful=False, open=False, acked=False)
```

The `post_incident()` method returns the full `Incident` record, as stored in
Argus. If you need it, you can get the incident ID from the the primary key
attribute `pk`, in case you need to address it directly later.

### Close an existing incident

Incidents are closed by posting a *END* type event to an incident's event
log, with an optional timestamp. The `Client` class provides the follow
convenience method for this operation:

```pycon
>>> from pyargus.client import Client
>>> from datetime import datetime
>>> c = Client(api_root_url="https://argus.example.org/api/v2", token="foobar")
>>> c.resolve_incident(incident=8, description="The demolition was cancelled", timestamp=datetime.now())
Event(pk=10, actor='testnav', description='The demolition was cancelled', incident=8, received=datetime.datetime(2021, 4, 22, 11, 47, 11, 978438, tzinfo=datetime.timezone(datetime.timedelta(seconds=7200), '+02:00')), timestamp=datetime.datetime(2021, 4, 22, 11, 47, 11, 946076, tzinfo=datetime.timezone(datetime.timedelta(seconds=7200), '+02:00')), type='END')
```

### Modify an existing incident

Argus does not allow modification of most incident attributes, but things
like the tag list can be changed. Modifications are made by constructing an
`Incident` object with the `pk` attribute set to the id of the incident you
wish you modify, and then adding values to the attributes you wish to modify:

```pycon
>>> from pyargus.client import Client
>>> from pyargus.models import Incident
>>> from datetime import datetime
>>> c = Client(api_root_url="https://argus.example.org/api/v2", token="foobar")
>>> i = Incident(
...     pk=8,
...     tags={
...         "host": "earth.example.org",
...         "location": "Milky way",
...     }
... )
>>> c.update_incident(i)
Incident(pk=8, start_time=datetime.datetime(2021, 4, 22, 11, 41, 53, 580947, tzinfo=datetime.timezone(datetime.timedelta(seconds=7200), '+02:00')), end_time=None, source=SourceSystem(pk=2, name='testnav', type='nav', user=3, base_url='http://localhost/'), source_incident_id='', details_url='', description='The earth was demolished to make way for a hyperspace bypass', level=None, ticket_url='', tags={'host': 'earth.example.org', 'location': 'Milky way'}, stateful=False, open=False, acked=False)

```

### Stateless incidents

Argus supports a concept of "stateless" incidents. Stateless incidents
represent single points in time, and do not have an end time. To explicitly
create stateless incidents, set the `end_time` attribute to the STATELESS
sentinel, like so:

```python
from datetime import datetime
from pyargus.models import Incident, STATELESS

stateless_incident = Incident(
    description="Something happened",
    start_time=datetime.now(),
    end_time=STATELESS
)
```

## BUGS

* Doesn't provide high-level error handling yet.
