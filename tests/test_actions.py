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

import actions as a
import skeleton_bots as sb


class TestActions(unittest.TestCase):

    # T101: ensures agent is able to recognise main emergency services and modify
    # other slots in a dynamic way correctly
    def test_validate_service_type(self):
        # set up new instance for service testing
        agent = a.ValidateServiceForm()

        # establish the bot state that is asking for a service
        dispatcher, tracker, domain = sb.service_bot()

        # test for 'police' being successfully parsed
        result = agent.validate_service_type("police", dispatcher, tracker, domain)
        self.assertEqual(result["service_type"], ["police"])
        # checks 'is_safe' slot is dynamically wiped
        self.assertIsNone(result["is_safe"])

        # test for 'ambulance' being successfully parsed
        result = agent.validate_service_type("ambulance", dispatcher, tracker, domain)
        self.assertEqual(result["service_type"], ["ambulance"])
        # check 'any_injured' slot is dynamically changed to 'yes' and 'victim_details' is wiped
        self.assertEqual(result["any_injured"], "Yes")
        self.assertIsNone(result["victim_details"])

        # test for 'fire department' being successfully parsed
        result = agent.validate_service_type("fire department", dispatcher, tracker, domain)
        self.assertEqual(result["service_type"], ["fire department"])
        # checks 'is_safe' slot is dynamically wiped
        self.assertIsNone(result["is_safe"])

        # tests agent can parse multiple instances of services
        result = agent.validate_service_type(["police", "ambulance"], dispatcher, tracker, domain)
        self.assertEqual(result["service_type"], ["police", "ambulance"])# checks 'is_safe' slot is dynamically wiped
        self.assertIsNone(result["is_safe"])
        # check 'any_injured' slot is dynamically changed to 'yes' and 'victim_details' is wiped
        self.assertEqual(result["any_injured"], "Yes")
        self.assertIsNone(result["victim_details"])

        result = agent.validate_service_type(["fire department", "ambulance"], dispatcher, tracker, domain)
        self.assertEqual(result["service_type"], ["fire department", "ambulance"])# checks 'is_safe' slot is dynamically wiped
        self.assertIsNone(result["is_safe"])
        # check 'any_injured' slot is dynamically changed to 'yes' and 'victim_details' is wiped
        self.assertEqual(result["any_injured"], "Yes")
        self.assertIsNone(result["victim_details"])

        result = agent.validate_service_type(["police", "fire department", "ambulance"], dispatcher, tracker, domain)
        self.assertEqual(result["service_type"], ["police", "fire department", "ambulance"])
        # checks 'is_safe' slot is dynamically wiped
        self.assertIsNone(result["is_safe"])
        # check 'any_injured' slot is dynamically changed to 'yes' and 'victim_details' is wiped
        self.assertEqual(result["any_injured"], "Yes")
        self.assertIsNone(result["victim_details"])

    # T102: validates Whitehall can infer required services from certain
    # emergency details
    def test_validate_emergency_details(self):
        # set up new instance for emergency testing
        agent = a.ValidateServiceForm()

        # establish the bot state that is asking for emergency details
        dispatcher, tracker, domain = sb.service_bot()

        # test that agent infers police and paramedics are needed when someone has been stabbed
        result = agent.validate_emergency_details("stabbing", dispatcher, tracker, domain)
        self.assertEqual(result["service_type"], ["police", "ambulance"])
        # assert that bot is aware someone has been injurred
        self.assertEqual(result["any_injured"], "Yes")

        # test that agent infers fire department needed when there is a fire
        result = agent.validate_emergency_details("fire", dispatcher, tracker, domain)
        self.assertEqual(result["service_type"], ["fire department"])

        # test that agent infers paramedics needed when someone is ahving a stroke
        result = agent.validate_emergency_details("stroke", dispatcher, tracker, domain)
        self.assertEqual(result["service_type"], ["ambulance"])

    # T103: confirms Whitehall correctly acknowledges answer from user when asking
    # if they are safe
    def test_validate_is_safe(self):
        # set up new instance for safety testing
        agent = a.ValidateServiceForm()

        # establish state where user is safe
        dispatcher, tracker, domain = sb.safe_bot("yes")
        # check method works for 'yes' replies
        result = agent.validate_is_safe("yeah i'm safe", dispatcher, tracker, domain)
        self.assertEqual(result["is_safe"], "Yes")
        self.assertEqual(dispatcher.messages[0]["text"], "Good, please make sure to keep safe")

        # establish state where user is not safe
        dispatcher, tracker, domain = sb.safe_bot("no")
        # check method works for 'no' replies
        result = agent.validate_is_safe("i'm not safe right now", dispatcher, tracker, domain)
        self.assertEqual(result["is_safe"], "No")
        self.assertEqual(dispatcher.messages[0]["text"], "Please get somewhere where you can be safe until someone arrives")

        # establish state where user is not safe
        dispatcher, tracker, domain = sb.safe_bot("unsure")
        # check method works for 'unsure' replies
        result = agent.validate_is_safe("i don't know", dispatcher, tracker, domain)
        self.assertEqual(result["is_safe"], "Unsure")
        self.assertEqual(dispatcher.messages[0]["text"], "Try and get somewhere safe until someone arrives")

    # T104: tests if Whitehall can accurately behave when user says someone is
    # injurred
    def test_validate_any_injured(self):
        # set up new instance for testing
        agent = a.ValidateServiceForm()

        # establish state where someone is injured
        dispatcher, tracker, domain = sb.injured_bot("yes")
        # check method works for 'yes' replies
        result = agent.validate_any_injured("my friend is injured, yeah", dispatcher, tracker, domain)
        # check ambulance is now part of the requested services
        self.assertIn("ambulance", result["service_type"])
        # check slot 'any_injured' is filled
        self.assertEqual(result["any_injured"], "Yes")
        # check slot 'victim_details' has correctly dynamically changed
        self.assertIsNone(result["victim_details"])

        # establish state where no one is injurred
        dispatcher, tracker, domain = sb.injured_bot("no")
        # check method works for 'yes' replies
        result = agent.validate_any_injured("no we're okay", dispatcher, tracker, domain)
        # check slot 'any_injured' is filled
        self.assertEqual(result["any_injured"], "No")

        # establish state where user is unsure
        dispatcher, tracker, domain = sb.injured_bot("unsure")
        # check method works for 'yes' replies
        result = agent.validate_any_injured("i'm not sure", dispatcher, tracker, domain)
        # check slot 'any_injured' is filled
        self.assertEqual(result["any_injured"], "Unsure")

    #T105: validates system can recognise real postcodes
    #T106: validates system will not store invalid postcodes, instead storing
    # user input for human validation
    def test_validate_form_postcode(self):
        # set up new instance for testing
        agent = a.ValidateServiceForm()

        # establish the bot state
        dispatcher, tracker, domain = sb.postcode_bot("valid")
        # checks valid postcode is accepted by system
        result = agent.validate_form_postcode("my postcode is cv4 8ge", dispatcher, tracker, domain)
        # checks the postcode is correctly parsed
        self.assertEqual(result["form_postcode"], "cv4 8ge")
        # checks system has made successful API call and has got district
        self.assertEqual(result["district"], "Coventry")

        # establish the bot state
        dispatcher, tracker, domain = sb.postcode_bot("invalid")
        # checks valid postcode is accepted by system
        result = agent.validate_form_postcode("the postcode is AA11 A11", dispatcher, tracker, domain)
        # checks system stored user input rather than an incorrect postcode
        self.assertEqual(result["form_postcode"], "the postcode is AA11 A11")
        # checks system has no notion of district from fake postcode
        self.assertNotIn("district", result)

    # T107: validates if Whitehall can provide approriate links to user
    # based on their emergency details
    def test_validate_first_aid(self):
        # set up new instance for testing
        agent = a.ValidateWrapupForm()

        # establish the new bot state
        dispatcher, tracker, domain = sb.first_aid_bot("stroke")
        result = agent.validate_first_aid("", dispatcher, tracker, domain)
        # check link is correct for stroke example
        self.assertEqual(dispatcher.messages[2]["text"], "https://www.redcross.org.uk/first-aid/learn-first-aid/stroke")

        # establish the new bot state
        dispatcher, tracker, domain = sb.first_aid_bot("covid")
        result = agent.validate_first_aid("", dispatcher, tracker, domain)
        # check link is correct for stroke example
        self.assertEqual(dispatcher.messages[2]["text"], "https://www.nhs.uk/conditions/coronavirus-covid-19/self-isolation-and-treatment/how-to-treat-symptoms-at-home/")

        # establish the new bot state
        dispatcher, tracker, domain = sb.first_aid_bot("bleeding")
        result = agent.validate_first_aid("", dispatcher, tracker, domain)
        # check link is correct for stroke example
        self.assertEqual(dispatcher.messages[2]["text"], "https://www.redcross.org.uk/first-aid/learn-first-aid/bleeding-heavily#:~:text=Put%20pressure%20on%20the%20wound,clot%20and%20stop%20the%20bleeding.&text=If%20you%20can't%20call,someone%20else%20to%20do%20it.")

        # establish the new bot state
        dispatcher, tracker, domain = sb.first_aid_bot("default")
        result = agent.validate_first_aid("", dispatcher, tracker, domain)
        # check link is given to aid user even if no specific links exist for emergency situation
        self.assertEqual(dispatcher.messages[2]["text"], "https://www.nhs.uk/conditions/first-aid/after-an-accident/")
