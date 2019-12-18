#%%

## Nick Newman OR 604 Homework00

import os
import csv
import sqlite3
import datetime as dt
from math import radians, cos, sin, asin, sqrt


#%%


# terminal number (col4), address (col3), latitude (col5), longitude (col6), docks = number of bikes + number of empty docks

# filepath is the file location of the locations csv file

def problem1():

    filepath = os.path.join(os.path.dirname(__file__), "Capital_Bike_Share_Locations.csv")
     
    locationsFile = open(filepath,"rt")
    locationsReader = csv.reader(locationsFile)
    next(locationsReader)
    
    bikeshare_db = "bikeshare_db.sqlite"
    conn = sqlite3.connect(bikeshare_db)
    cur = conn.cursor()
    
    cur.execute("PRAGMA TABLE_INFO(locations);")
    
    #if the table does not exist, create it
    if len(cur.fetchall()) == 0:       
        
        createTableSQL = """CREATE TABLE locations
                            (TERMINAL_NUMBER integer,
                            ADDRESS text,
                            LATITUDE real,
                            LONGITUDE real,
                            DOCKS integer);"""
           
        cur.execute(createTableSQL)
        conn.commit()
            
        tempList = [] 
        for row in locationsReader:
            tempList.append([row[3], row[2], row[4], row[5], int(row[11]) + int(row[12])])
        
        print("{}\t{} {}".format(os.path.basename(filepath), len(tempList), "Records Inserted"))
        cur.executemany('INSERT INTO locations VALUES(?,?,?,?,?);',tempList)
        conn.commit()

    else:
        print("Table 'locations' already exists\n")
        

    tableListQuery = "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY Name;"
    cur.execute(tableListQuery)
    tables = map(lambda t: t[0], cur.fetchall())
    totalTables = 0
    print("")
    for table in tables:
        cur.execute("PRAGMA TABLE_INFO({});".format(table))
        numberColumns = len(cur.fetchall())
        
        cur.execute("SELECT COUNT() FROM {};".format(table))
        numberRows = cur.fetchone()[0]
        
        numberCells = numberColumns * numberRows
        
        if totalTables == 0:
            print("{:10}\t{:>10}\t{:>10}\t{:>10}".format("Table Name","Columns","Rows","Cells"))
        totalTables += 1
        
        print("{:10}\t{:10}\t{:10}\t{:10}".format(table, numberColumns, numberRows, numberCells))
    
    print("")
    print("Number of tables: \t{}".format(totalTables))
    
    conn.close()

print("Starting Problem 1\n")
problem1()
print("Problem 1 is complete\n")


#%%

# Problem 2

# filepath is the location of the folder with all the bikeshare trip data
def problem2():
    
    
    bikeshare_db = "bikeshare_db.sqlite"
    conn = sqlite3.connect(bikeshare_db)
    cur = conn.cursor()

    cur.execute("PRAGMA TABLE_INFO(trips);")
    
    #if the table does not exist, create it
    if len(cur.fetchall()) == 0:       
        createTrips = """CREATE TABLE trips
                            (TRIP_DURATION integer,
                            START_DATE text,
                            START_STATION integer,
                            STOP_DATE text,
                            STOP_STATION integer,
                            BIKE_ID text,
                            USER_TYPE text);"""
            
        cur.execute(createTrips)
        conn.commit()
        
    
        tempList = []
    
        filepath = os.path.dirname(__file__)
        for filename in os.listdir(filepath):
            if "Year" in filename:
                file = open(filepath + "\\" + filename, "rt")
                tripReader = csv.reader(file)
                next(tripReader)
            
            
                for row in tripReader:
                    row[1] = dt.datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d %H:%M")
                    row[3] = dt.datetime.strptime(row[3], '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d %H:%M")
                    tempList.append(row)
                
                print("{}\t{} {}".format(filename, len(tempList), "Records Inserted"))
        
                cur.executemany("INSERT INTO trips VALUES(?,?,?,?,?,?,?);", tempList)
                conn.commit()
                tempList = []


    else:
        print("Table 'trips' already exists\n")
    
    
    tableListQuery = "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY Name;"
    cur.execute(tableListQuery)
    tables = map(lambda t: t[0], cur.fetchall())
    totalTables = 0
    print("")
    for table in tables:
        cur.execute("PRAGMA TABLE_INFO({});".format(table))
        numberColumns = len(cur.fetchall())
        
        cur.execute("SELECT COUNT() FROM {};".format(table))
        numberRows = cur.fetchone()[0]
        
        numberCells = numberColumns * numberRows
        
        if totalTables == 0:
            print("{:10}\t{:>10}\t{:>10}\t{:>10}".format("Table Name","Columns","Rows","Cells"))
        totalTables += 1
        
        print("{:10}\t{:10}\t{:10}\t{:10}".format(table, numberColumns, numberRows, numberCells))
    
    print("")
    print("Number of tables: \t{}".format(totalTables))
    
    conn.close()

print("Starting problem 2\n")
problem2()
print("Problem 2 is complete\n")

#%%

# Problem 3

def haversine(lon1, lat1, lon2, lat2, unit):
    
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    # Radius of earth in kilometers is 6371
    # Radius in mi is 3956
    if unit == "km":
        km = 6371 * c
        return km
    else:
        mi = 3959 * c
        return mi

print("Haversine function has been created. Default distance is miles")
print("Problem 3 is complete\n")
    

#%%
        
#Problem 4


def problem4(units):
    

    bikeshare_db = "bikeshare_db.sqlite"
    conn = sqlite3.connect(bikeshare_db)
    cur = conn.cursor()
    
    rowsQuery = """SELECT a.TERMINAL_NUMBER || '-' || b.TERMINAL_NUMBER TERMINALS, a.LATITUDE, a.LONGITUDE, b.LATITUDE, b.LONGITUDE FROM 
    locations a, locations b 
    WHERE a.TERMINAL_NUMBER <= b.TERMINAL_NUMBER
    AND a.TERMINAL_NUMBER != b.TERMINAL_NUMBER;"""
    cur.execute(rowsQuery)
    numberOfRows = cur.fetchall()
    
    station = []
    tempDist = []
    
    for row in numberOfRows:
        station1 = row[0]
        distance = haversine(row[2], row[1], row[4], row[3], units)
        tempDist.append(distance)
        station.append(station1)
        
    station_dist = dict(zip(station, tempDist))
    return station_dist


print("Problem 4 is complete\n")



#%%

# Problem 5

def terminal_distance():

    units = str(input("What unit would you like to use? ('mi' or 'km') "))

    dictionary = problem4(units)
    terminal = str(input("What is the station you'd like to start with? (Choose station between 31000 and 32221) "))
    distance = float(input("What is distance you'd like to use for nearby stations? "))
    filtered_dict = {k:v for k,v in dictionary.items() if len(terminal) == 5 and terminal in k}
    filtered_dict = {k:v for k,v in filtered_dict.items() if v <= distance}

    
    for key, value in sorted(filtered_dict.items(), key = lambda kv: kv[1]):
        print("{} {:.2f} {}".format(key, value, units))


print("Problem 5 is complete")
print("use function 'terminal_distance' in order to run the function to your specifications\n")

#%%

def problem6():
    station1 = input("What is the first station? (Choose station between 31000 and 32221)")
    station2 = input("What is the second station? (Choose station between 31000 and 32221)")
    date1 = str(input("What is the first date? (Y-m-d format)"))
    date2 = str(input("What is the second date? (Y-m-d format)"))
    bikeshare_db = "bikeshare_db.sqlite"
    conn = sqlite3.connect(bikeshare_db)
    cur = conn.cursor()
    rowsQuery = """SELECT COUNT(*) FROM trips WHERE (START_STATION = {st1} AND STOP_STATION = {st2} AND START_DATE >= strftime('%Y-%m-%d %H:%M', ?) AND STOP_DATE <= strftime('%Y-%m-%d %H:%M', ?)) OR (START_STATION = {st2} AND STOP_STATION = {st1} 
    AND START_DATE >=  strftime('%Y-%m-%d %H:%M', ?) AND STOP_DATE <=  strftime('%Y-%m-%d %H:%M', ?));""".format(st1 = station1, st2 = station2)
    cur.execute(rowsQuery, (date1, date2, date1, date2))
    numberOfRows = cur.fetchone()[0]


    print("The number of records between stations {} and {} and dates {} and {} is {}".format(station1, station2, date1, date2, numberOfRows))

print("problem 6 is complete")
print("use function 'problem6' in order to run the function to your specifications")
