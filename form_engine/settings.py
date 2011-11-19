# -*- coding: utf-8 -*-
import os.path
from apps.form_engine.views import *

FORMS_MEDIA_ROOT = os.path.join(
	os.path.dirname(__file__), 'static'
	)