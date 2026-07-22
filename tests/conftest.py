import os

import django


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "web.config.settings",
)
django.setup()
