# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk import Tracker, FormValidationAction
from rasa_sdk.types import DomainDict

# for api calls
import urllib.request as req
import json


# gets data from api calls
def getAPIResult(url):
    return json.loads(req.urlopen(url).read())

class ValidateServiceForm(FormValidationAction):

    # keep track of what services the user explicitly asks for
    explicit_service_type = []

    def name(self) -> Text:
        return "validate_service_form"

    @staticmethod
    # hotlist of common emergencies and their associated service types for
    # derriving the required emergency service
    def emergency_hot_list() -> Dict[Text, List[Text]]:
        hotlist = {"stabbing": ["police", "ambulance"],
                   "fire": ["ambulance", "fire department"]}
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

        # check to see if more services are required other than those explicitly stated
        for s in implicit_service_type:
            if not (s in self.explicit_service_type):
                self.explicit_service_type.append(s)

        return {"emergency_details": slot_value,
                "service_type": self.explicit_service_type}

class ValidatePoliceForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_police_form"

    # possible api if free: https://osdatahub.os.uk/docs
    def validate_street_address(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        #
        return {"street_address": slot_value}


    def validate_postcode(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # if empty then no valid value
        if not slot_value:
            return {"postcode": None}

        # if there was only 1 classifier that found a postcode
        if isinstance(slot_value, str):
            postcode = slot_value
        # else there are two, meaning a ReGeX version and one from DIETClassifier,
        # which is most likely incorrect
        else:
            postcode = slot_value[0]

        url = "https://api.postcodes.io/postcodes/{}/validate".format(postcode)
        # remove possible space in postcode
        url = url.replace(" ", "")
        # check postcode is valid
        result = json.loads(req.urlopen(url).read())["result"]
        # if postcode isn't valid then don't accept
        if not result:
            return {"postcode": None}
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

        # only return 1 string to eliminate issue with multiple classifiers
        return {"postcode": postcode}


class ValidateAmbulanceFormForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_ambulance_form"

    @staticmethod
    # hotlist matching victim details with useful links to help user
    # apply first aid
    def medical_hot_list() -> Dict[Text, Text]:
        hotlist = {"bleeding": "https://www.redcross.org.uk/first-aid/learn-first-aid/bleeding-heavily#:~:text=Put%20pressure%20on%20the%20wound,clot%20and%20stop%20the%20bleeding.&text=If%20you%20can't%20call,someone%20else%20to%20do%20it.",
                   "heart attack": "https://www.redcross.org.uk/first-aid/learn-first-aid/heart-attack#:~:text=Help%20the%20person%20to%20sit%20down.&text=Sitting%20will%20ease%20the%20strain,hurt%20themselves%20if%20they%20collapse",
                   "stroke": "https://www.redcross.org.uk/first-aid/learn-first-aid/stroke",
                   "nausea": "https://www.nhs.uk/conditions/feeling-sick-nausea/",
                   "COVID-19": "https://www.nhs.uk/conditions/coronavirus-covid-19/self-isolation-and-treatment/how-to-treat-symptoms-at-home/"}
        # default options:
        # https://www.nhs.uk/conditions/first-aid/after-an-accident/
        # https://www.nhs.uk/common-health-questions/accidents-first-aid-and-treatments/
        return hotlist


    def validate_victim_details(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # if empty then no valid set of victim details
        if not slot_value:
          return {"victim_details": None}

        links = []
        hotlist = self.medical_hot_list()

        # if only 1 detail, search hotlist directly
        if isinstance(slot_value, str):
            # if victim detail has useful link associated
            if slot_value in hotlist:
                # save the link for later use
                links.append(hotlist[slot_value])
            # else no associated useful link, so provide default
            else:
                links.append("https://www.nhs.uk/common-health-questions/accidents-first-aid-and-treatments/")
        # else is a list and each must be searched for separately
        else:
            for v in slot_value:
                # if victim detail has useful link associated
                if v in hotlist:
                    # save the link for later use
                    links.append(hotlist[v])
            # if no links found, include fallback default
            if not links:
                links.append("https://www.nhs.uk/common-health-questions/accidents-first-aid-and-treatments/")

        for l in links:
            print(l)

        return {"victim_details": slot_value}



    # possible api if free: https://osdatahub.os.uk/docs
    def validate_street_address(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        #
        return {"street_address": slot_value}

    def validate_postcode(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        # if empty then no valid value
        if not slot_value:
            return {"postcode": None}

        # if there was only 1 classifier that found a postcode
        if isinstance(slot_value, str):
            postcode = slot_value
        # else there are two, meaning a ReGeX version and one from DIETClassifier,
        # which is most likely incorrect
        else:
            postcode = slot_value[0]

        url = "https://api.postcodes.io/postcodes/{}/validate".format(postcode)
        # remove possible space in postcode
        url = url.replace(" ", "")
        # check postcode is valid
        result = json.loads(req.urlopen(url).read())["result"]
        # if postcode isn't valid then don't accept
        if not result:
            return {"postcode": None}
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

        # only return 1 string to eliminate issue with multiple classifiers
        return {"postcode": postcode}
