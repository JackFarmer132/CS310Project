from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk import Tracker, FormValidationAction
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet

import sqlite3
import pathlib

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# for api calls
import urllib.request as req
import json

import unittest
import pathlib
import sys

path = str(pathlib.Path(__file__).parent.absolute().parent.absolute())
path += "/chatbot/actions"
sys.path.append(path)

from actions import ActionGenerateReport as a
import skeleton_bots as sb

class TestActions(unittest.TestCase):

    def setUp(self):
        self.dispatcher, self.tracker, self.domain = sb.service_bot()
