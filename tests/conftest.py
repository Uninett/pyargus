def pytest_configure(config):
    # This forces an argus version that works (as of this writing, 1.33 is the
    # latest, but the docker image for it is broken)
    config.option.argus_version = "1.30.0"
