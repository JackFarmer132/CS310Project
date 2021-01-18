import sqlite3

conn = sqlite3.connect('conversations.db')

c = conn.cursor()


# # create table again if ever deleted
# c.execute("""CREATE TABLE conversations (
#             id integer primary key,
#             Requested_Services text,
#             Emergency_Details text,
#             Safe text,
#             Someone_Injured text,
#             Victim_Details text,
#             Street_Address text,
#             Postcode text,
#             District text,
#             Location_Description text,
#             First_Aid_Knowledge text,
#             Name text,
#             Phone_Number text,
#             Extra_Details text
#             )""")


# # clears table
# c.execute("DELETE FROM conversations WHERE id>0")


# sample insert for current table
print(c.execute("""INSERT INTO conversations(
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
            Extra_Details) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("police, ambulance",
            "stabbing",
            "No",
            "Yes",
            "bleeding",
            "Unknown",
            "Unknown",
            "Unknown",
            "there's a tree",
            "Yes",
            "Jack",
            "I'd rather not",
            "nope")).lastrowid)

cur_id = 10
# select everything from table
c.execute("SELECT * FROM conversations WHERE id=?", (int(cur_id),))

# print all entries
for i, val in enumerate(c.fetchone()):
    print(i)
    print(val)
print(c.fetchone())


conn.commit()
conn.close()
