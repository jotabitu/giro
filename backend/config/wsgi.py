import os

from django.core.wsgi import get_wsgi_application

# Sem padrão: processo que esquece a variável não sobe com config.settings.dev (C-04).
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    raise RuntimeError("Defina DJANGO_SETTINGS_MODULE (config.settings.dev, .test ou .prod).")
application = get_wsgi_application()
