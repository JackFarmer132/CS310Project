# https://rasa.com/docs/rasa/custom-actions

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


# gets data from api calls
def getAPIResult(url):
    return json.loads(req.urlopen(url).read())


# certain slots need to be given an initial value to prevent the chatbot from
# asking irrelevant detials (like victim info when there's no victim). doing
# this all in a custom action is better than doing it in the form (like before)
class ActionInitSlots(Action):
    def name(self):
        return "action_init_slots"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: DomainDict) -> Dict[Text, Any]:
        # sets the slots that start as not None
        return [SlotSet("victim_details", "No Victim"),
                SlotSet("location_description", "Not Needed"),
                SlotSet("first_aid", "Not Relevant"),
                SlotSet("is_safe", "Irrelevant")]


# there will be some cases where asking about first aid is not relevant,
# namely when there is no victim. if there is a victim, it will ask about
# first aid experience
class ActionManageFirstAid(Action):
    def name(self):
        return "action_manage_first_aid"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: DomainDict) -> Dict[Text, Any]:

        victim_details = tracker.slots.get("victim_details")
        if victim_details and not (victim_details == "No Victim"):
            return [SlotSet("first_aid", None)]


class ActionSaveServiceInfo(Action):
    def name(self):
        return "action_save_service_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: DomainDict) -> Dict[Text, Any]:
        #collect slot values for storing
        saved_slots = {}

        saved_slots["Requested Services"] = tracker.slots.get("service_type")
        saved_slots["Emergency Details"] = tracker.slots.get("emergency_details")
        saved_slots["Safe"] = tracker.slots.get("is_safe")
        saved_slots["Someone Injured"] = tracker.slots.get("any_injured")
        saved_slots["Victim Details"] = tracker.slots.get("victim_details")
        saved_slots["Street Address"] = tracker.slots.get("street_address")
        saved_slots["Postcode"] = tracker.slots.get("postcode")
        saved_slots["Location Description"] = tracker.slots.get("location_description")
        saved_slots["District"] = tracker.slots.get("district")
        if not saved_slots["District"]:
            saved_slots["District"] = "Unknown"

        # turn any lists into readable strings
        for k in saved_slots:
            val = saved_slots[k]
            if val:
                # if slot value is a list, need to convert to string
                if not isinstance(val, str):
                    val = ", ".join(val)
                    saved_slots[k] = val

        # get path of database
        path = str(pathlib.Path(__file__).parent.absolute().parent.absolute().parent.absolute())
        path += "/frontend/whitehall/conversations.db"

        conn = sqlite3.connect(path)
        c = conn.cursor()

        # initialise query
        c.execute("""INSERT INTO conversations(
                    Requested_Services,
                    Emergency_Details,
                    Safe,
                    Someone_Injured,
                    Victim_Details,
                    Street_Address,
                    Postcode,
                    District,
                    Location_Description,
                    First_Aid_Knowledge,
                    Name,
                    Phone_Number,
                    Extra_Details,
                    Report) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (str(saved_slots["Requested Services"]),
                    str(saved_slots["Emergency Details"]),
                    str(saved_slots["Safe"]),
                    str(saved_slots["Someone Injured"]),
                    str(saved_slots["Victim Details"]),
                    str(saved_slots["Street Address"]),
                    str(saved_slots["Postcode"]),
                    str(saved_slots["District"]),
                    str(saved_slots["Location Description"]),
                    "Unknown",
                    "Unknown",
                    "Unknown",
                    "Unknown",
                    "-"))

        # run insert query
        conn.commit()
        conn.close()


class ActionSaveWrapupInfo(Action):
    def name(self):
        return "action_save_wrapup_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: DomainDict) -> Dict[Text, Any]:
        #collect slot values for storing
        saved_slots = {}

        saved_slots["First Aid Knowledge"] = tracker.slots.get("first_aid")
        saved_slots["Name"] = tracker.slots.get("name")
        saved_slots["Phone Number"] = tracker.slots.get("phone_number")
        saved_slots["Extra Details"] = tracker.slots.get("extra_details")

        # get path of database
        path = str(pathlib.Path(__file__).parent.absolute().parent.absolute().parent.absolute())
        path += "/frontend/whitehall/conversations.db"

        conn = sqlite3.connect(path)
        c = conn.cursor()

        # get id of the last inserted row
        c.execute("""SELECT * FROM conversations
                    ORDER BY id DESC
                    LIMIT 1""")
        cur_id = c.fetchone()[0]

        # update row with new values
        c.execute("""UPDATE conversations SET
                    First_Aid_Knowledge=?,
                    Name=?,
                    Phone_Number=?,
                    Extra_Details=? WHERE id=?""",
                    (str(saved_slots["First Aid Knowledge"]),
                    str(saved_slots["Name"]),
                    str(saved_slots["Phone Number"]),
                    str(saved_slots["Extra Details"]),
                    int(cur_id)))

        # run update query
        conn.commit()
        conn.close()


class ActionGenerateReport(Action):
    def name(self):
        return "action_generate_report"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: DomainDict) -> Dict[Text, Any]:

        styles = getSampleStyleSheet()
        headingStyle = ParagraphStyle(name="left", alignment=TA_CENTER, fontSize=13, leading=10)

        data = [
            [Paragraph("<b>Slot</b>", headingStyle),
             Paragraph("<b>User Response</b>", headingStyle)]
        ]

        # get path of database
        path = str(pathlib.Path(__file__).parent.absolute().parent.absolute().parent.absolute())
        path += "/frontend/whitehall/conversations.db"

        conn = sqlite3.connect(path)
        c = conn.cursor()

        # get id of the last inserted row
        c.execute("""SELECT * FROM conversations
                    ORDER BY id DESC
                    LIMIT 1""")
        cur_id = int(c.fetchone()[0])

        # get the appropriate row
        c.execute("SELECT * FROM conversations WHERE id=?", (cur_id,))

        # link data from db into array for pdf
        for i, val in enumerate(c.fetchone()):
            if i == 1:
                data.append(self.prepare_report("Requested Services", val))
            elif i == 2:
                data.append(self.prepare_report("Emergency Details", val))
            elif i == 3:
                data.append(self.prepare_report("Safe", val))
            elif i == 4:
                data.append(self.prepare_report("Someone Injured", val))
            elif i == 5:
                data.append(self.prepare_report("Victim Details", val))
            elif i == 6:
                data.append(self.prepare_report("Street Address", val))
            elif i == 7:
                data.append(self.prepare_report("Postcode", val))
            elif i == 8:
                data.append(self.prepare_report("District", val))
            elif i == 9:
                data.append(self.prepare_report("Location Description", val))
            elif i == 10:
                data.append(self.prepare_report("First Aid Knowledge", val))
            elif i == 11:
                data.append(self.prepare_report("Name", val))
            elif i == 12:
                data.append(self.prepare_report("Phone Number", val))
            elif i == 13:
                data.append(self.prepare_report("Extra Details", val))

        # get transcript of whole conversation
        transcript = ""
        # help eliminate duplicates
        last = ""

        for dict in tracker.events:
            if dict['event'] == "user":
                speaker = "<b>User</b>"
                text = dict['text'].capitalize()
                # if bot was restarted, ignore what has been done so far
                if text == "/restart":
                    transcript = ""
                    last = "<b>Whitehall</b>"
                else:
                    if not (speaker == last):
                        transcript += speaker + ": " + text + "<br/>"
                        last = speaker
            elif dict['event'] == "bot":
                speaker = "<b>Whitehall</b>"
                text = dict['text']
                transcript += speaker + ": " + text + "<br/>"
                last = speaker

        transcript = Paragraph(transcript, styles['Normal'])
        data.append([Paragraph("<b>Transcript</b>", styles['Normal']), transcript])

        pdf_path = self.make_pdf(data, cur_id)

        c.execute("""UPDATE conversations SET
                    Report=?  WHERE id=?""",
                    (str(pdf_path),
                    int(cur_id)))

        # run update query
        conn.commit()
        conn.close()


    # formats the text correctly for insertion into pdf report
    def prepare_report(self, slot_name, slot_val):

        styles = getSampleStyleSheet()

        slot_val = (slot_val.lower()).capitalize()
        slot_name = Paragraph(("<b>" + slot_name + "</b>"), styles['Normal'])
        slot_val = Paragraph(slot_val, styles['Normal'])

        return [slot_name, slot_val]


    # uses data from run to make a table in a pdf
    def make_pdf(self, data, id):

        path = str(pathlib.Path(__file__).parent.absolute().parent.absolute().parent.absolute())
        path += "/frontend/whitehall/reports/"

        file_name = path + "report_" + str(id) + ".pdf"
        pdf = SimpleDocTemplate(file_name, pagesize=letter)
        table = Table(data, colWidths=(2*inch, 5*inch))
        style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.darkgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('VALIGN', (0, 1), (0, -1), 'TOP'),

        ])
        table.setStyle(style)

        # alternating row colours
        row_num = len(data)
        for i in range(1, row_num):
            if (i % 2) == 0:
                ts = TableStyle(
                    [('BACKGROUND', (0,i), (-1,i), colors.lightgrey)]
                )
                table.setStyle(ts)

        # add borders
        ts = TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ])
        table.setStyle(ts)

        elements = []
        elements.append(table)

        pdf.build(elements)

        return file_name


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
                   "COVID": ["ambulance"],
                   "dead": ["ambulance"]}
        return hotlist


    def validate_service_type(self, slot_value: Any, dispatcher: CollectingDispatcher,
                              tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

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

        # if ambulance was not requested, no victim
        if "ambulance" in slot_value:
            victim_details = tracker.slots.get("victim_details")
            # if bot thought no victim, then wipe slot to allow asking about them
            if victim_details == "No Victim":
                return_dict["victim_details"] = None
            # prevents asking if anyone is injured since clearly someone is
            return_dict["any_injured"] = "Yes"

        # only want to ask if safe if there's a fire or crime, so check that
        # service is requested
        safe = tracker.slots.get("is_safe")
        # only wipes if not answered yet
        if ("police" in slot_value or "fire department" in slot_value) and (safe == "Irrelevant"):
            # wipe slot so bot will now ask about it to fill again
            return_dict["is_safe"] = None

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

        # makes sure it doesn't save [] as the service type value
        if explicit_service_type == []:
            explicit_service_type = None

        return_dict["service_type"] = explicit_service_type
        return_dict["service_type_memory"] = explicit_service_type

        # if ambulance was not requested, no victim
        if (explicit_service_type) and ("ambulance" in explicit_service_type):
            victim_details = tracker.slots.get("victim_details")
            # if bot thought no victim, then wipe slot to allow asking about them
            if victim_details == "No Victim":
                return_dict["victim_details"] = None
            # prevents asking if anyone is injured since clearly someone is
            return_dict["any_injured"] = "Yes"

        # only want to ask if safe if there's a fire or crime, so check that
        # service is requested
        safe = tracker.slots.get("is_safe")
        # only wipes if not answered yet
        if (explicit_service_type) and ("police" in explicit_service_type or "fire department" in explicit_service_type) and (safe == "Irrelevant"):
            # wipe slot so bot will now ask about it to fill again
            return_dict["is_safe"] = None

        return return_dict


    def validate_is_safe(self, slot_value: Any, dispatcher: CollectingDispatcher,
                         tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        # if victim safe, continue
        if (tracker.latest_message['intent'].get('name') == "answer_yes"):
            return {"is_safe": "Yes"}
        # otherwise prompt user to get to safety
        elif (tracker.latest_message['intent'].get('name') == "answer_no"):
            ####################################################################
            return {"is_safe": "No"}
        elif (tracker.latest_message['intent'].get('name') == "answer_unsure"):
            ####################################################################
            return {"is_safe": "Unsure"}
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
            return_dict["any_injured"] = "Yes"
            return_dict["victim_details"] = None

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
            return_dict["any_injured"] = "No"
        elif (tracker.latest_message['intent'].get('name') == "answer_unsure"):
            return_dict["any_injured"] = "Unsure"
        else:
            return_dict["any_injured"] = slot_value

        return return_dict


    def validate_victim_details(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        # if only being initialised, then accept it
        if slot_value == "No Victim":
            return {"victim_details": slot_value}
        # otherwise it's been updated during runtime
        else:
            return_dict = {}

            # there is someone injured, so save this info
            return_dict["any_injured"] = "Yes"
            # get current services required and add ambulance if not there
            services = tracker.slots.get("service_type")
            # if a string, make it a list
            if isinstance(services, str):
                services = [services]

            if (services) and ("ambulance" not in services) :
                services.append("ambulance")
                return_dict["service_type"] = services
                return_dict["service_type_memory"] = services
            # else if services is empty, add ambulance to it
            elif not services:
                services = ["ambulance"]

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
        return_dict["form_street_address"] = slot_value
        return return_dict


    # possible api if free: https://osdatahub.os.uk/docs
    def validate_form_street_address(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        street_address = tracker.slots.get("street_address")
        postcode = tracker.slots.get("postcode")
        return_dict = {}

        # if there is an entity for the street address, save it
        if street_address:
            return_dict["street_address"] = street_address
            return_dict["form_street_address"] = slot_value
        # if not but user did have intent to do so, may have missed so save
        elif (tracker.latest_message['intent'].get('name') == "give_location"):
            # saves all text from user input for human to read
            return_dict["street_address"] = slot_value
            return_dict["form_street_address"] = slot_value
        # if user is unsure of where they are, will ask to describe location
        elif ((tracker.latest_message['intent'].get('name') == "answer_unsure") or
              (tracker.latest_message['intent'].get('name') == "answer_no")):
            return_dict["street_address"] = "Unknown"
            return_dict["form_street_address"] = slot_value
            # free up this slot so bot will now ask about it
            return_dict["location_description"] = None
            # if postcode then keep it, otherwise set to Unknown since user
            # probably doesn't know it
            if not postcode:
                return_dict["postcode"] = "Unknown"
                return_dict["form_postcode"] = slot_value
        else:
            # utters message saying it didn't understand, assume they don't know
            dispatcher.utter_message(text="Sorry, I didn't understand that just then")
            return_dict["street_address"] = "Unknown"
            return_dict["form_street_address"] = slot_value
            return_dict["location_description"] = None
            if not postcode:
                return_dict["postcode"] = "Unknown"
                return_dict["form_postcode"] = slot_value

        return return_dict


    def validate_location_description(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                      tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        # just save as the user textual input since is a description for humans
        return {"location_description": slot_value}


    def validate_postcode(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        # if street address is given, don't ask again
        return_dict = {}

        # if there was only 1 classifier that found a postcode
        if isinstance(slot_value, str):
            postcode = slot_value
        # else there are two, meaning a ReGeX version and one from DIETClassifier,
        # which is most likely incorrect
        else:
            postcode = slot_value[0]

        return_dict["postcode"] = postcode
        return_dict["form_postcode"] = postcode
        return return_dict


    def validate_form_postcode(self, slot_value: Any, dispatcher: CollectingDispatcher,
                          tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        return_dict = {}

        # gets the actual postcode if it exists
        postcode = tracker.slots.get("postcode")

        # if an actual postcode was found, then save it here
        if postcode:
            # if there was only 1 classifier that found a postcode
            if isinstance(postcode, str):
                postcode = postcode
            # else there are two, meaning a ReGeX version and one from DIETClassifier,
            # which is most likely incorrect
            else:
                postcode = postcode[0]

            url = "https://api.postcodes.io/postcodes/{}/validate".format(postcode)
            # remove possible space in postcode
            url = url.replace(" ", "")
            # check postcode is valid
            result = json.loads(req.urlopen(url).read())["result"]
            # if postcode isn't valid then hopefully human can understand
            if not result:
                return {"form_postcode": slot_value,
                        "postcode": slot_value}

            # add valid postcode assignment to return dictionary
            return_dict["form_postcode"] = postcode

            # get new URL that will fetch information on validated postcode
            url = url.replace("/validate", "")
            result = json.loads(req.urlopen(url).read())["result"]

            # get relevant data from postcode
            # https://postcodes.io/docs
            district = result["admin_district"]
            county = result["admin_county"]
            ccg = result["ccg"]

            # if district is not None from postocde search, set slot
            if district:
                return_dict["district"] = district

            return return_dict
        # else postcode not given, so assume person doesn't know it
        else:
            return {"form_postcode": slot_value,
                    "postcode": slot_value}


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

        # if being initialised, just set as slot value
        if slot_value == "Not Relevant":
            return {"first_aid": slot_value}
        # else is being set from user interaction
        else:
            return_dict = {}

            # get the victim details to search for useful links
            victim_details = tracker.slots.get("victim_details")
            links = []

            # load in associated symptoms and medical links
            hotlist = self.medical_hot_list()

            # if victim safe, continue
            if (tracker.latest_message['intent'].get('name') == "answer_yes"):
                return_dict["first_aid"] = "Yes"
                dispatcher.utter_message(text="Okay, if you feel you can help the situation, please do")
            # otherwise prompt user to get to safety
            elif (tracker.latest_message['intent'].get('name') == "answer_no"):
                return_dict["first_aid"] = "No"
                dispatcher.utter_message(text="Okay, I will find some useful resources to help you")
            else:
                return_dict["first_aid"] = "Unknown"
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

            # get the plural right
            if len(links) > 1:
                dispatcher.utter_message(text="Here are some links that I found that can help:")
            else:
                dispatcher.utter_message(text="Here is a useful link that I found that can help:")

            for l in links:
                dispatcher.utter_message(text=l)

            return return_dict


    def validate_name(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        # if there was only 1 classifier that found a name
        if isinstance(slot_value, str):
            name = slot_value
        # else there are two, meaning a ReGeX version and one from DIETClassifier,
        # which is most likely incorrect
        else:
            name = slot_value[0]

        # if valid name is found, don't ask again
        return_dict = {}
        return_dict["name"] = name
        return_dict["form_name"] = name
        return return_dict


    def validate_form_name(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                      tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        # just save as the user textual input since is a description for humans
        return {"name": slot_value,
                "form_name": slot_value}


    def validate_phone_number(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        # if there was only 1 classifier that found a phone number
        if isinstance(slot_value, str):
            phone_number = slot_value
        # else there are two, meaning a ReGeX version and one from DIETClassifier,
        # which is most likely incorrect
        else:
            phone_number = slot_value[0]

        # if valid phone number is found, don't ask again
        return_dict = {}
        return_dict["phone_number"] = phone_number
        return_dict["form_phone_number"] = phone_number
        return return_dict


    def validate_form_phone_number(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                      tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        # just save as the user textual input since is a description for humans
        return {"phone_number": slot_value,
                "form_phone_number": slot_value}


    def validate_extra_details(self, slot_value: Any, dispatcher: CollectingDispatcher,
                                      tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:

        # just save as the user textual input since is a description for humans
        return {"extra_details": slot_value}
