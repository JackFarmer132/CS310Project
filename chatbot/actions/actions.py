# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk import Tracker, FormValidationAction
from rasa_sdk.types import DomainDict

class ActionHelloWorld(Action):

    def name(self) -> Text:
        return "action_hello_world"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Hello World!")

        return []

class ValidateTestForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_test_form"

    @staticmethod
    def service_db() -> List[Text]:
        # database of the supported emegency service types
        return ["police", "ambulance", "fire department"]

    def validate_service_type(self, slot_value: Any, dispatcher: CollectingDispatcher,
                        tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        # if empty then no valid service type
        if not slot_value:
            return {"service_type": None}

        # check each type is in the valid range
        for s in slot_value:
            if not (s.lower() in self.service_db()):
                return {"service_type": None}

        # only here if valid so return as such
        return {"service_type": slot_value}

    def validate_name(self, slot_value: Any, dispatcher: CollectingDispatcher,
                        tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        return {"name": slot_value}


    def validate_phone_number(self, slot_value: Any, dispatcher: CollectingDispatcher,
                        tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        return {"phone_number": slot_value}
