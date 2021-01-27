from django.http import HttpResponse
from django.shortcuts import render
import sqlite3
import pathlib

# Create your views here.
def home_view(request, *args, **kwargs):
    return render(request, "home.html", {})

# Create your views here.
def data_view(request, *args, **kwargs):
    return render(request, "data.html", {})

def about_view(request, *args, **kwargs):

    # get path of database
    path = str(pathlib.Path(__file__).parent.absolute().parent.absolute())
    path += "/conversations.db"
    print(path)
    conn = sqlite3.connect(path)

    c = conn.cursor()
    c.execute("SELECT * FROM conversations WHERE id>0")

    cur_entry = []

    # link data from db with names
    for entry in c.fetchall():
        db_data = []
        for i, val in enumerate(entry):
            if i == 0:
                db_data.append(["Id", val])
            elif i == 1:
                db_data.append(["Requested Services", val])
            elif i == 2:
                db_data.append(["Emergency Details", val])
            elif i == 3:
                db_data.append(["Safe", val])
            elif i == 4:
                db_data.append(["Someone Injured", val])
            elif i == 5:
                db_data.append(["Victim Details", val])
            elif i == 6:
                db_data.append(["Street Address", val])
            elif i == 7:
                db_data.append(["Postcode", val])
            elif i == 8:
                db_data.append(["District", val])
            elif i == 9:
                db_data.append(["Location Description", val])
            elif i == 10:
                db_data.append(["First Aid Knowledge", val])
            elif i == 11:
                db_data.append(["Name", val])
            elif i == 12:
                db_data.append(["Phone Number", val])
            elif i == 13:
                db_data.append(["Extra Details", val])
            elif i == 14:
                db_data.append(["Report", val])
        cur_entry.append(db_data)

    my_context = {
        "my_text": "database stuff",
        "my_number": 123,
        "cur_entry": cur_entry
    }

    conn.commit()
    conn.close()

    return render(request, "about.html", my_context)
