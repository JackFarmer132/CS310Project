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

# class ValidateTestForm(FormValidationAction):
#     def name(self) -> Text:
#         return "validate_test_form"
#
#     @staticmethod
#     def service_db() -> List[Text]:
#         # database of the supported emegency service types
#         return ["police", "ambulance", "fire department"]
#
#     def validate_service_type(self, slot_value: Any, dispatcher: CollectingDispatcher,
#                         tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
#
#         # if empty then no valid service type
#         if not slot_value:
#             return {"service_type": None}
#
#         # check each type is in the valid range
#         for s in slot_value:
#             if not (s.lower() in self.service_db()):
#                 return {"service_type": None}
#
#         # only here if valid so return as such
#         return {"service_type": slot_value}
#
#     def validate_name(self, slot_value: Any, dispatcher: CollectingDispatcher,
#                         tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
#         return {"name": slot_value}
#
#
#     def validate_phone_number(self, slot_value: Any, dispatcher: CollectingDispatcher,
#                         tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
#         return {"phone_number": slot_value}


class ValidateServiceForm(FormValidationAction):

    # keep track of what services the user explicitly asks for
    explicit_service_type = []

    def name(self) -> Text:
        return "validate_service_form"

    @staticmethod
    # hot list of common emergencies and their associated service types for
    # derriving the required emergency service
    def emergency_hot_list() -> Dict[Text, List[Text]]:
        hotlist = {"stabbing": ["police", "ambulance"]}
        return hotlist

    def validate_service_type(self, slot_value: Any, dispatcher: CollectingDispatcher,
                        tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # if empty then no valid service type
        if not slot_value:
            return {"service_type": None}

        # if entry is only 1 type of service, is a string
        if isinstance(slot_value, str):
            self.explicit_service_type.append(slot_value)
        # otherwise is a non-empty list
        else:
            self.explicit_service_type = slot_value

        # only here if valid so return as such
        return {"service_type": slot_value}

    def validate_emergency_details(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                  tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        # if empty then no valid set of emergency details
        if not slot_value:
          return {"emergency_details": None}

        # holds any implicitly required services based on emergency details
        implicit_service_type = []
        # get local hotlist for finding implicit service types
        hotlist = self.emergency_hot_list()

        # if only 1 detail, search hotlist directly
        if isinstance(slot_value, str):
            # if there are saved services associated with detail
            if slot_value in hotlist:
                # add the required services to service_type
                for s in hotlist.get(slot_value):
                    implicit_service_type.append(s)
            # else no way to guess as service, so return as normal
            else:
                return {"emergency_details": slot_value}
        # else is a list and each must be searched for separately
        else:
            for e in slot_value:
                # if there are saved services associated with detail
                if e in hotlist:
                    # add the required services to service_type
                    for s in hotlist.get(e, None):
                        implicit_service_type.append(s)
                # else no way to guess as service, so return as normal
                else:
                    return {"emergency_details": slot_value}

        # check to see if more services are required other than those explicitly stated
        for s in implicit_service_type:
            if not (s in self.explicit_service_type):
                self.explicit_service_type.append(s)

        return {"emergency_details": slot_value,
                "service_type": self.explicit_service_type}
