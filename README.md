Argus API Client
================

This is the official Python client library for the 
[Argus](https://github.com/Uninett/Argus) API server.

The Argus server is an incident registry, capable of aggregating alerts from 
multiple source systems. Argus also can send event notifications (via e-mail,
SMS, etc.) when incidents are created or resolved.

Usage examples
==============

Listing open incidents that have not been acknowledged:

```python
from pyargus.client import Client

c = Client(api_root_url="https://argus.example.org/api/v1", token="foobar")
for incident in c.get_incidents(open=True, acked=False):
    print(incident)
```


BUGS
====
* Doesn't provide high-level error handling yet.
