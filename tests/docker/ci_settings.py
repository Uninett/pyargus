"""Site settings for running argus server in an integration test harness"""

from argus.site.settings.backend import *

# Allow all hosts, since all requests will typically come from outside the container
ALLOWED_HOSTS = ["*"]
DEBUG = True
