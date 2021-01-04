# https://rasa.com/docs/rasa/custom-actions

from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk import Tracker, FormValidationAction
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet

# for api calls
import urllib.request as req
import json


# gets data from api calls
def getAPIResult(url):
    return json.loads(req.urlopen(url).read())

class ValidateServiceForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_service_form"

    @staticmethod
    # hotlist of common emergencies and their associated service types for
    # derriving the required emergency service
    def emergency_hot_list() -> Dict[Text, List[Text]]:
        hotlist = {"stabbing": ["police", "ambulance"],
                   "fire": ["fire department"],
                   "stroke": ["ambulance"],
                   "COVID": ["ambulance"]}
        return hotlist


    def validate_service_type(self, slot_value: Any, dispatcher: CollectingDispatcher,
                              tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # if empty then no valid service type
        if not slot_value:
            return {"service_type": None}

        return_dict = {}

        # if entry is only 1 entity, is string and needs to be list
        if isinstance(slot_value, str):
            slot_value = [slot_value]

        # get current requested services
        cur_service_type = tracker.slots.get("service_type_memory")

        # if other serivces have been requested, need to append new one(s)
        if cur_service_type:
            # if entry is only 1 entity, is string and needs to be list
            if isinstance(cur_service_type, str):
                cur_service_type = [cur_service_type]

            # append and remove duplicates
            slot_value = slot_value + cur_service_type
            slot_value = list(dict.fromkeys(slot_value))

        # removes invalid service types
        for s in slot_value:
            s.lower()
            if (s != "police") and (s != "ambulance") and (s != "fire department"):
                slot_value.remove(s)

        return_dict["service_type"] = slot_value
        return_dict["service_type_memory"] = slot_value

        print(slot_value)
        print(("ambulance" not in slot_value))
        # if ambulance was not requested, no victim
        if ("ambulance" not in slot_value):
            return_dict["victim_details"] = "No Victim"
        else:
            victim_details = tracker.slots.get("victim_details")
            # if bot thought no victim, then wipe slot to allow asking about them
            if victim_details == "No Victim":
                return_dict["victim_details"] = None
            return_dict["first_aid"] = None
            return_dict["any_injured"] = "yes"

        return return_dict


    def validate_emergency_details(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                   tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # if empty then no valid set of emergency details
        if not slot_value:
          return {"emergency_details": None}

        return_dict = {}

        # gets current emergency details to append new ones
        cur_emergency_details = tracker.slots.get("emergency_details_memory")

        if cur_emergency_details:
            # if entry is only 1 entity, is string and needs to be list
            if isinstance(cur_emergency_details, str):
                cur_emergency_details = [cur_emergency_details]

            # if entry is only 1 entity, is string and needs to be list
            if isinstance(slot_value, str):
                slot_value = [slot_value]

            # append and remove duplicates
            slot_value = slot_value + cur_emergency_details
            slot_value = list(dict.fromkeys(slot_value))

        return_dict["emergency_details"] = slot_value
        return_dict["emergency_details_memory"] = slot_value

        # initialise these here since this always happens, so guaranteed to init
        # only set location description if it hasn't been set yet (None)
        location_description = tracker.slots.get("location_description")
        if location_description == None:
            return_dict["location_description"] = "Not Needed"

        # only set first aid to 'not needed' if it is currently None
        first_aid = tracker.slots.get("first_aid")
        if first_aid == None:
            return_dict["first_aid"] = "Not Needed"

        explicit_service_type = tracker.slots.get("service_type")

        # if entry is only 1 type of service, is string and needs to be list
        if isinstance(explicit_service_type, str):
            explicit_service_type = [explicit_service_type]

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
                return return_dict
        # else is a list and each must be searched for separately
        else:
            for e in slot_value:
                # if there are saved services associated with detail
                if e in hotlist:
                    # add the required services to service_type
                    for s in hotlist.get(e, None):
                        implicit_service_type.append(s)

        if explicit_service_type:
            explicit_service_type = explicit_service_type + implicit_service_type
        else:
            explicit_service_type = implicit_service_type
        # remove duplicates
        explicit_service_type = list(dict.fromkeys(explicit_service_type))

        return_dict["service_type"] = explicit_service_type
        return_dict["service_type_memory"] = explicit_service_type

        print(return_dict)

        # if ambulance was not requested, no victim
        if ("ambulance" not in explicit_service_type):
            return_dict["victim_details"] = "No Victim"
        else:
            return_dict["victim_details"] = None
            return_dict["first_aid"] = None
            return_dict["any_injured"] = "Yes"
        return return_dict


    def validate_is_safe(self, slot_value: Any, dispatcher: CollectingDispatcher,
                         tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # if victim safe, continue
        if (tracker.latest_message['intent'].get('name') == "answer_yes"):
            return {"is_safe": "yes"}
        # otherwise prompt user to get to safety
        elif (tracker.latest_message['intent'].get('name') == "answer_no"):
            ####################################################################
            return {"is_safe": "no"}
        elif (tracker.latest_message['intent'].get('name') == "answer_unsure"):
            ####################################################################
            return {"is_safe": "unsure"}
        # otherwise answer wasn't given, but no need to re-ask
        else:
            ####################################################################
            # return text user gave in case hman user can make more sense of it than bot
            return {"is_safe": slot_value}


    def validate_any_injured(self, slot_value: Any, dispatcher: CollectingDispatcher,
                             tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        return_dict = {}

        # if someone is injured, add ambulance to list of required services
        if (tracker.latest_message['intent'].get('name') == "answer_yes"):
            return_dict["any_injured"] = "yes"
            return_dict["victim_details"] = None
            return_dict["first_aid"] = None
            return_dict["victim_details_memory"] = None

            # get list of services and add ambulance if not already there
            services = tracker.slots.get("service_type")

            if "ambulance" not in services:
                # if string then needs turning into an array
                if isinstance(services, str):
                    services = [services]
                services.append("ambulance")

            return_dict["service_type"] = services
            return_dict["service_type_memory"] = slot_value
        # otherwise likely no one is injured
        elif (tracker.latest_message['intent'].get('name') == "answer_no"):
            return_dict["any_injured"] = "no"
        elif (tracker.latest_message['intent'].get('name') == "answer_unsure"):
            return_dict["any_injured"] = "unsure"
        else:
            return_dict["any_injured"] = slot_value

        return return_dict


    def validate_victim_details(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # if empty then no valid set of victim details
        if not slot_value:
          return {"victim_details": None}

        return_dict = {}

        # if first aid is "Not Needed", need to change here since victim present
        first_aid = tracker.slots.get("first_aid")
        if first_aid == "Not Needed":
            return_dict["first_aid"] = None

        # prevents current list of victim details from being overwritten
        cur_victim_details = tracker.slots.get("victim_details_memory")

        if cur_victim_details and not (cur_victim_details == "No Victim"):
            # if entry is only 1 entity, is string and needs to be list
            if isinstance(cur_victim_details, str):
                cur_victim_details = [cur_victim_details]

            # if entry is only 1 entity, is string and needs to be list
            if isinstance(slot_value, str):
                slot_value = [slot_value]

            # append and remove duplicates
            slot_value = slot_value + cur_victim_details
            slot_value = list(dict.fromkeys(slot_value))

        return_dict["victim_details"] = slot_value
        return_dict["victim_details_memory"] = slot_value

        return return_dict


    def validate_street_address(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # if street address is given, don't ask again
        return_dict = {}
        return_dict["street_address"] = slot_value
        return_dict["location"] = slot_value
        return return_dict


    # possible api if free: https://osdatahub.os.uk/docs
    def validate_location(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        street_address = tracker.slots.get("street_address")
        return_dict = {}

        # if there is an entity for the street address, save it
        if street_address:
            return_dict["street_address"] = street_address
            return_dict["location"] = slot_value
        # if not but user did have intent to do so, may have missed so save
        elif (tracker.latest_message['intent'].get('name') == "give_location"):
            # saves all text from user input for human to read
            return_dict["street_address"] = slot_value
            return_dict["location"] = slot_value
        # if user is unsure of where they are, will ask to describe location
        elif ((tracker.latest_message['intent'].get('name') == "answer_unsure") or
              (tracker.latest_message['intent'].get('name') == "answer_no")):
            return_dict["street_address"] = "Unknown"
            return_dict["location_description"] = None
            # don't ask for postcode since probably don't know
            return_dict["postcode"] = "Unknown"
            return_dict["location"] = slot_value
        # otherwise probably didn't provide location, so re-ask
        else:
            return_dict["location"] = None

        return return_dict


    def validate_location_description(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                      tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # just save as the user textual input since is a description for humans
        return {"location_description": slot_value}


    def validate_postcode(self, slot_value: Any, dispatcher: CollectingDispatcher,
                          tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        return_dict = {}

        # if user is unsure of postcode, accept it and move on
        if (tracker.latest_message['intent'].get('name') == "answer_unsure"):
            return_dict["postcode"] = "Unknown"

        # if there was only 1 classifier that found a postcode
        if isinstance(slot_value, str):
            postcode = slot_value
        # else there are two, meaning a ReGeX version and one from DIETClassifier,
        # which is most likely incorrect
        else:
            postcode = slot_value[0]

        # if postcode, validate it
        if postcode:
            url = "https://api.postcodes.io/postcodes/{}/validate".format(postcode)
            # remove possible space in postcode
            url = url.replace(" ", "")
            # check postcode is valid
            result = json.loads(req.urlopen(url).read())["result"]
            # if postcode isn't valid then don't accept
            if not result:
                return {"postcode": None}

            # add valid postode assignment to return dictionary
            return_dict["postcode"] = postcode

            # get new URL that will fetch information on validated postcode
            url = url.replace("/validate", "")
            result = json.loads(req.urlopen(url).read())["result"]

            # get relevant data from postcode
            # https://postcodes.io/docs
            district = result["admin_district"]
            county = result["admin_county"]
            ccg = result["ccg"]
            print(result)
            print(district)
            print(county)
            print(ccg)

            # if district is not None from postocde search, set slot
            if district:
                return_dict["district"] = district

            return return_dict
        else:
            return {"postcode": slot_value}


class ValidateWrapupForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_wrapup_form"


    @staticmethod
    # hotlist matching victim details with useful links to help user
    # apply first aid
    def medical_hot_list() -> Dict[Text, Text]:
        hotlist = {"bleeding": "https://www.redcross.org.uk/first-aid/learn-first-aid/bleeding-heavily#:~:text=Put%20pressure%20on%20the%20wound,clot%20and%20stop%20the%20bleeding.&text=If%20you%20can't%20call,someone%20else%20to%20do%20it.",
                   "heart attack": "https://www.redcross.org.uk/first-aid/learn-first-aid/heart-attack#:~:text=Help%20the%20person%20to%20sit%20down.&text=Sitting%20will%20ease%20the%20strain,hurt%20themselves%20if%20they%20collapse",
                   "stroke": "https://www.redcross.org.uk/first-aid/learn-first-aid/stroke",
                   "nausea": "https://www.nhs.uk/conditions/feeling-sick-nausea/",
                   "COVID-19": "https://www.nhs.uk/conditions/coronavirus-covid-19/self-isolation-and-treatment/how-to-treat-symptoms-at-home/",
                   "__default__": "https://www.nhs.uk/conditions/first-aid/after-an-accident/"}
        # default options:
        # https://www.nhs.uk/conditions/first-aid/after-an-accident/
        # https://www.nhs.uk/common-health-questions/accidents-first-aid-and-treatments/
        return hotlist


    def validate_first_aid(self, slot_value: Any, dispatcher: CollectingDispatcher,
                           tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        return_dict = {}

        # only do this if the first aid is required (not "Not Needed")#
        if slot_value == "Not Needed":
            return_dict["first_aid"] = slot_value
        else:
            # get the victim details to search for useful links
            victim_details = tracker.slots.get("victim_details")
            links = []

            # load in associated symptoms and medical links
            hotlist = self.medical_hot_list()
            print("hello")

            # if victim safe, continue
            if (tracker.latest_message['intent'].get('name') == "answer_yes"):
                return_dict["first_aid"] = "yes"
                print("yes")
                dispatcher.utter_message(text="Okay, if you feel you can help the situation, please do")
            # otherwise prompt user to get to safety
            elif (tracker.latest_message['intent'].get('name') == "answer_no"):
                return_dict["first_aid"] = "no"
                dispatcher.utter_message(text="Okay, I will find some useful resources to help you")
            else:
                return_dict["first_aid"] = "unknown"
                dispatcher.utter_message(text="Okay, I will find some useful resources to help you")

            # if only 1 detail, search hotlist directly
            if isinstance(victim_details, str):
                # if victim detail has useful link associated
                if victim_details in hotlist:
                    # save the link for later use
                    links.append(hotlist[victim_details])
                # else no associated useful link, so provide default
                else:
                    links.append(hotlist["__default__"])
            # else is a list and each must be searched for separately
            else:
                for v in victim_details:
                    # if victim detail has useful link associated
                    if v in hotlist:
                        # save the link for later use
                        links.append(hotlist[v])
                # if no links found, include fallback default
                if not links:
                    links.append(hotlist["__default__"])

            dispatcher.utter_message(text="Here are some links that I found that can help:")
            for l in links:
                print(l)
                dispatcher.utter_message(text=l)

        return return_dict


    def validate_name(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                      tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # just save as the user textual input since is a description for humans
        return {"name": slot_value}


    def validate_phone_number(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                      tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # just save as the user textual input since is a description for humans
        return {"phone_number": slot_value}


    def validate_extra_details(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                      tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # just save as the user textual input since is a description for humans
        return {"extra_details": slot_value}


# there will be some cases where asking about first aid is not relevant,
# namely when there is no victim. if there is no victim, this will ensure the
# bot doesn't ask
class ActionManageFirstAid(Action):
    def name(self):
        return "action_manage_first_aid"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: DomainDict) -> Dict[Text, Any]:

        victim_details = tracker.slots.get("victim_details")
        if not victim_details:
            return [SlotSet("first_aid", "Not Needed")]
