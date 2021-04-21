Whitehall is a conversational agent that fulfils the role of an emergency call handler. It will learn information from conversations and store them for moderation and evaluation.



Getting Whitehall Working

•	Install the required dependencies
•	In one terminal, navigate to /CS310Project/chatbot and run the following: 'rasa run -m models --enable-api --cors "*" --debug'
•	In a second terminal, again navigate to /CS310Project/chatbot and run the following: 'rasa run actions’
•	In a third terminal, navigate to /CS310Project/frontend/whitehall and run the following: ‘python manage.py runserver’
•	Use link provided by the third terminal to enter the user interface



Using the Shell

•	In one terminal, navigate to /CS310Project/chatbot and run the following: 'rasa shell’
•	In a second terminal, again navigate to /CS310Project/chatbot and run the following: 'rasa run actions’
•	This provides the default interface for Whitehall, which may be preferable. One can use ‘rasa shell –debug’ to see stages of processing



Running Tests

•	To run unit tests, navigate to /CS310Project/tests and run the following: ‘python -m unittest test_actions.py’
•	To test the performance of the NLP system, navigate to /CS310Project/chatbot and run the following: ‘rasa test nlu --nlu data/nlu.yml --cross-validation’ (note: will take a while to complete). Results can be found in /CS310Project/chatbot/results
•	To test the performance of the conversation accuracy, navigate to /CS310Project/chatbot and run the following: ‘rasa test’. Results can be found in /CS310Project/chatbot/results



Training data can be found at /CS310Project/chatbot/data, with the files holding the raw nlp-data and forms for directing conversation live.


Whitehall is compatible with Facebook Messenger, although setting up this feature must be redone for every fresh instance. Access to the account used by Whitehall is also needed, meaning Messenger use is reliant on developer involvement.
