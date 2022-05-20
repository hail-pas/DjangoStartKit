import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
import django  # noqa

django.setup()
