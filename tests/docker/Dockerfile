FROM ghcr.io/uninett/argus:1.29.0

RUN mkdir -p /extrapython
COPY ci_settings.py /extrapython/ci_settings.py
ENV PYTHONPATH=/extrapython
ENV DJANGO_SETTINGS_MODULE=ci_settings
