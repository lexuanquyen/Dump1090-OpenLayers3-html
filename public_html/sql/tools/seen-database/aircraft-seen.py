#!/usr/bin/python

#================================================================================#
#                             ADS-B FEEDER PORTAL                                #
# ------------------------------------------------------------------------------ #
# Copyright and Licensing Information:                                           #
#                                                                                #
# The MIT License (MIT)                                                          #
#                                                                                #
# Adapted 2016 Ed Allan Kissack                                                  #
# Original Copyright (c) 2015-2016 Joseph A. Prochazka                           #
#                                                                                #
# Permission is hereby granted, free of charge, to any person obtaining a copy   #
# of this software and associated documentation files (the "Software"), to deal  #
# in the Software without restriction, including without limitation the rights   #
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell      #
# copies of the Software, and to permit persons to whom the Software is          #
# furnished to do so, subject to the following conditions:                       #
#                                                                                #
# The above copyright notice and this permission notice shall be included in all #
# copies or substantial portions of the Software.                                #
#                                                                                #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR     #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,       #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE    #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER         #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,  #
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE  #
# SOFTWARE.                                                                      #
#================================================================================#

# WHAT THIS DOES:                                                 
# ---------------------------------------------------------------
#
# 1) Read aircraft.json generated by dump1090-mutability.
# 2) Check if the icao is in the seen database
# 3) Update the last time the flight was seen if it is
# 4) If it isnt in the seen database add it 
#
# REQUIRED PACKAGES:
# ---------------------------------------------------------------
# python-mysqldb


import datetime
import json
import MySQLdb
import sqlite3
import time
import os


# Read the configuration file.
with open(os.path.dirname(os.path.realpath(__file__)) + '/config-seen.json') as config_file:
    config = json.load(config_file)

while True:

    # Read dump1090-mutability's aircraft.json.
    with open('/run/dump1090-mutability/aircraft.json') as data_file:
        data = json.load(data_file)

    ## Connect to a MySQL database.
    db = MySQLdb.connect(host=config["database"]["host"], user=config["database"]["user"], \
         passwd=config["database"]["passwd"], db=config["database"]["dbase"])

    # Assign the time and/or data to a variable.
    date_now = datetime.datetime.now().strftime("%Y-%m-%d")
 
    cursor = db.cursor()

    for aircraft in data["aircraft"]:
        # -------  Set some variables -----------
        a_hex = aircraft["hex"].strip()
	if a_hex.startswith("~"): a_hex = a_hex[1:]  ##  have seen some like ~94e011  google suggest .strip(" ~") for space and ~

        # -- Seen DATABASE QUERY ----------------------------------------------------------------------------------------
        cursor.execute("SELECT firstseen, lastseen FROM Seen WHERE icao = %s", a_hex)
        # ------------------------------------------------------------------------------------------------------------------------
        row_data = cursor.fetchall()
        row_count = cursor.rowcount
        for row in row_data:
            data_firstseen = row[0]
            data_lastseen  = row[1]
        if row_count == 0:
            # -------------------------------
            # -- NEW AIRCRAFT FOR DATABASE --
            # -------------------------------
	    # Should see if it is in the master database, as if so we can bring accross type and priority

            print(" ** %s Added **" % (a_hex))
            cursor.execute("INSERT INTO Seen (icao, firstseen, lastseen, seen) VALUES (%s, %s, %s, 1)", ( a_hex,  date_now,  date_now) )
        else:
            # -------------------------------------
            # -- In Seen, MAYBE UPDATE? --
            # -------------------------------------
            masterNeedsUpdate = 0

            if data_firstseen == ""  or data_firstseen is None:
                 if data_lastseen == ""  or data_lastseen is None:
                      firstTime = date_now
                 else:
                      firstTime = data_lastseen
                 masterNeedsUpdate = 1
            else:
                 firstTime = data_firstseen

            if data_lastseen == "" or data_lastseen is None:
                 lastTime = date_now
                 masterNeedsUpdate = 1
            else:
                 if data_lastseen != date_now:
                      lastTime = date_now
                      masterNeedsUpdate = 1
                 else:
                      lastTime = data_lastseen

            if masterNeedsUpdate == 1 and a_hex != '000000' :

                cursor.execute("SELECT seen, lastseen FROM Seen WHERE icao = %s", a_hex)
                row_data = cursor.fetchall()
                row_count = cursor.rowcount
                for row in row_data:
                    seencnt = row[0]
                    seenlst = row[1]
                if row_count != 0:
                    if seenlst != date_now:
                        seencnt = seencnt + 1     
                    print(" +1 %s" % (a_hex))
                    cursor.execute("UPDATE Seen SET firstseen = %s, lastseen = %s, seen = %s WHERE icao = %s", (firstTime, lastTime, seencnt, a_hex))

    # Close the database connection.
    db.commit()
    db.close()
    time.sleep(15)
