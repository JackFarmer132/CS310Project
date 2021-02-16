from django.http import HttpResponse
from django.shortcuts import render
import sqlite3
import pathlib

# Create your views here.
def home_view(request, *args, **kwargs):
    return render(request, "home.html", {})


def about_view(request, *args, **kwargs):
    return render(request, "about.html", {})

def data_view(request, *args, **kwargs):

    # get path of database
    path = str(pathlib.Path(__file__).parent.absolute().parent.absolute())
    path += "/conversations.db"
    conn = sqlite3.connect(path)

    c = conn.cursor()
    c.execute("SELECT * FROM conversations WHERE id>0")

    cur_entry = []

    # link data from db with names
    for entry in c.fetchall():
        db_data = []
        for i, val in enumerate(entry):
            db_data.append(str(val))
        # only include if report exists
        if db_data[14] != "-":
            cur_entry.append(db_data)

    my_context = {
        "cur_entry": cur_entry
    }

    conn.commit()
    conn.close()

    return render(request, "data.html", my_context)

def chatroom_view(request, *args, **kwargs):
    return render(request, "chatroom.html", {})

def noisy_chatroom_view(request, *args, **kwargs):
    return render(request, "noisy_chatroom.html", {})
