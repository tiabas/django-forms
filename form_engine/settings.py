import os.path
from form_engine.views import *

FORMS_MEDIA_ROOT = os.path.join(
	os.path.dirname(__file__), 'static'
	)