# Homework03 Problem 1 ################################################
from gurobipy import *
import csv

def problem1():
    
    filepath = os.path.join(os.path.dirname(__file__))
    slot_machines = {}
    with open(os.path.join(filepath, "slots.csv"),"rt") as myfile:
        slotsReader = csv.reader(myfile)
        next(slotsReader)
        for row in slotsReader:
            slot_machines[row[0]] = (int(row[1]), int(row[2]),float(row[3]),float(row[4]))
    
    floors = {}
    with open(os.path.join(filepath, "floors.csv"), "rt") as myfile:
        floorReader = csv.reader(myfile)
        next(floorReader)
        for row in floorReader:
            floors[row[0]] = int(row[1])
    
    MaintLimit = 835
    
    gamble = Model()
    gamble.modelSense = GRB.MAXIMIZE
    
    gamble.update()
    
    mix = {}
    for slot in slot_machines:
        for floor in floors:
            mix[slot, floor] = gamble.addVar(vtype = GRB.CONTINUOUS,
                                   obj = slot_machines[slot][0],
                                   name = (slot + floor))
   
   
    # machine type on hand 
    gambleConstrs = {}
    for slot in slot_machines:
        constrName = 'OnHand_' + slot
        gambleConstrs[constrName] = gamble.addConstr(quicksum(mix[slot, floor] for floor in floors) <= 
                                                             slot_machines[slot][1], name = constrName)
    
    
    # floor space constraint
    for floor in floors:
        constrName = 'FloorSpace_' + floor
        gambleConstrs[constrName] = gamble.addConstr(quicksum(mix[slot, floor] * slot_machines[slot][3] for slot in slot_machines) <= floors[floor], name = constrName)
    
    # maintenance constraint
    gambleConstrs['maxmaint'] = gamble.addConstr(quicksum(mix[slot, floor] * slot_machines[slot][2]
                                                for slot in slot_machines for floor in floors) <= MaintLimit, name = 'maxmaint')
            
    gamble.update()

    gamble.write('gamble.lp')
    
    gamble.optimize()
    
    gamble.write('gamble.sol')

  
    mySolList = []
    print("\n Variable Results")
    for m in mix:
        if mix[m].x > 0:
            print (mix[m].VarName, mix[m].x)
            mySolList.append((mix[m].VarName, mix[m].x))
    
        
    import sqlite3
      
    gamble_db = "gamble.sqlite"
    conn = sqlite3.connect(gamble_db)
    cur = conn.cursor()
    
    cur.execute("PRAGMA TABLE_INFO(p1_solution);")
    if len(cur.fetchall()) == 0:
        
        createTableSQL = """CREATE TABLE p1_solution
                                    (VARIABLE text,
                                    VALUE real);"""
    
        cur.execute(createTableSQL)
        conn.commit()
    
        cur.executemany("INSERT INTO p1_solution VALUES(?,?)",mySolList)
        conn.commit()
    
    else:
        print("\np1_solution table already exists")
    
    cur.execute("SELECT * FROM p1_solution;")
    print("\nSQL Results for database 'gamble.sqlite':")
    print(cur.fetchall())
    conn.close()
    
print("\nUse function problem1() to run problem 1")



# Problem 3 #####################################################

## importing data and loading it into a database
## supplier data, dominos daily demand, and good dominos data (store location info)
import sqlite3
import os
import csv
from gurobipy import *
    
def problem3():
    

    filepath = os.path.join(os.path.dirname(__file__)) 

    fileStore = open(os.path.join(filepath,"OR604 Good Dominos Data.csv"), "rt")
    fileSupplier = open(os.path.join(filepath, "Distributor_Data.csv"), "rt")
    fileDemand = open(os.path.join(filepath,"OR 604 Dominos Daily Demand.csv"), "rt")
    
    
    StoreReader = csv.reader(fileStore)
    next(StoreReader)
    SupplierReader = csv.reader(fileSupplier)
    next(SupplierReader)
    DemandReader = csv.reader(fileDemand)
    next(DemandReader)
    
    dominos_db = "dominos_db.sqlite"
    conn = sqlite3.connect(dominos_db)
    cur = conn.cursor()
    
    cur.execute("""DROP TABLE IF EXISTS dominos_data;""")
    cur.execute("""DROP TABLE IF EXISTS supplier;""")
    cur.execute("""DROP TABLE IF EXISTS demand;""")
    
    
    createGoodDominos = """CREATE TABLE dominos_data
                            (STORE_NUMBER integer,
                            STORE text,
                            STREET text,
                            CITY text,
                            STATE text,
                            ZIP integer,
                            LATITUDE real,
                            LONGITUDE real);"""
                            
    createSupplier = """CREATE TABLE supplier
                        (DC_ID text,
                        ADDRESS text,
                        LATITUDE real,
                        LONGITUDE real,
                        SUPPLY_CAPACITY real,
                        DIST_COST real);"""
                        
    createDemand = """CREATE TABLE demand
                        (DATE text,
                        STORE_NUMBER integer,
                        PIZZA_SALES integer);"""
                        
    cur.execute(createGoodDominos)
    cur.execute(createSupplier)
    cur.execute(createDemand)
    conn.commit()
    
    
    tempList = []
    for row in StoreReader:
        tempList.append([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]])
    cur.executemany('INSERT INTO dominos_data VALUES(?,?,?,?,?,?,?,?);', tempList)
    conn.commit()
    
    
    tempList = []
    for row in SupplierReader:
        tempList.append([row[0], row[1], row[2], row[3], row[4], row[5]])
    cur.executemany('INSERT INTO supplier VALUES(?,?,?,?,?,?);', tempList)
    conn.commit()
    
    tempList = []
    for row in DemandReader:
        tempList.append([row[0], row[1], row[2]])
    cur.executemany('INSERT INTO demand VALUES(?,?,?);', tempList)
    conn.commit()
    
       
    fileDemand.close()
    fileStore.close()
    fileSupplier.close()

    # info about each table just inserted into the database
    tableListQuery = "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY NAME;"
    cur.execute(tableListQuery)
    tables = map(lambda t: t[0], cur.fetchall())
    totalTables = 0
    for table in tables:
        cur.execute("PRAGMA TABLE_INFO({});".format(table))
        numberColumns = len(cur.fetchall())
        
        cur.execute("SELECT COUNT() FROM {};".format(table))
        numberRows = cur.fetchone()[0]
        
        if totalTables == 0:
            print("{:10}\t{:>10}\t{:>10}".format("Table Name","Columns","Rows"))
        totalTables += 1
        
        print("{:10}\t{:10}\t{:10}".format(table, numberColumns, numberRows))

    print("")
    

    # deleting stores not in good store but in daily demand
    # 12 stores
    cur.execute("""SELECT DISTINCT(STORE_NUMBER) FROM demand WHERE STORE_NUMBER 
                 NOT IN (SELECT STORE_NUMBER FROM dominos_data)""")
    
    missing_stores = cur.fetchall()
    
    cur.execute("""DELETE FROM demand WHERE STORE_NUMBER 
                 NOT IN (SELECT STORE_NUMBER FROM dominos_data)""")
    
    cur.fetchall()
    conn.commit()
    
    print("There are {} stores missing from the store data and they were deleted\n".format(len(missing_stores)))


    # stores in good store data but not in the daily demand data
    # 29 stores
    cur.execute("""SELECT STORE_NUMBER FROM dominos_data WHERE STORE_NUMBER 
                 NOT IN (SELECT STORE_NUMBER FROM demand)""")
    missing_demand = cur.fetchall()

    # creating a tuple with the distributor names
    cur.execute("""SELECT DC_ID FROM supplier""")
    rowQuery = cur.fetchall()
    
    distributors = []
    for row in rowQuery:
        distributors.append(row[0].replace(" ",""))
    
    
    # creating a table with the store numbers
    cur.execute("""SELECT STORE_NUMBER FROM dominos_data""")
    rowQuery = cur.fetchall()

    stores = []
    for row in rowQuery:
        stores.append(row[0])
    
    
    # creating a dictionary with the average weekly demand for every store
    #   the average demand across all stores was calculated and this value 
    #   was used for the stores with missing demand data
    ## demand constraint #####   
    dominos_db = "dominos_db.sqlite"
    conn = sqlite3.connect(dominos_db)
    cur = conn.cursor()
    
    cur.execute("""SELECT AVG(PIZZA_SALES) FROM demand;""")
    avg_sales = cur.fetchall()
     
    
    cur.execute("""SELECT STORE_NUMBER, AVG(PIZZA_SALES) FROM demand 
                GROUP BY STORE_NUMBER;""")
                
    rowQuery = cur.fetchall()
    
    store = []
    demand = []
    
    for row in rowQuery:
        demand.append(row[1] * 7)
        store.append(row[0])
        
        

    
    cur.execute("""SELECT STORE_NUMBER FROM dominos_data WHERE STORE_NUMBER 
             NOT IN (SELECT STORE_NUMBER FROM demand)""")
    
    rowQuery = cur.fetchall()
    
    for row in rowQuery:
        demand.append(avg_sales[0][0] * 7)
        store.append(row[0])
        
        
    
    store_demand = dict(zip(store, demand))
    print("{} stores required a proxy value and that value was {}, which is "
          "the average weekly demand across all stores\n".format(len(missing_demand), avg_sales[0][0]*7))


    # creating a haversine distance function
    from math import radians, cos, sin, asin, sqrt
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



    # creating a dictionary with the keys being the names of the stores and 
    #   distributors and the values being the distance between the two in miles
    # distance constraint #####
    dominos_db = "dominos_db.sqlite"
    conn = sqlite3.connect(dominos_db)
    cur = conn.cursor()
    
    rowsQuery = """SELECT s.DC_ID, d.STORE_NUMBER , s.LATITUDE, s.LONGITUDE, d.LATITUDE, d.LONGITUDE FROM 
    dominos_data d, supplier s;"""
    cur.execute(rowsQuery)
    numberOfRows = cur.fetchall()
    
    store = []
    tempDist = []
    
    for row in numberOfRows:
        store1 = (row[0].replace(" ",""),row[1])
        distance = haversine(row[3], row[2], row[5], row[4], "mi")
        tempDist.append(distance)
        store.append(store1)
        
    store_dist = dict(zip(store, tempDist))


    # creating a dictionary with the cost per mile for each distribution center
    # cost constraint #####
    dominos_db = "dominos_db.sqlite"
    conn = sqlite3.connect(dominos_db)
    cur = conn.cursor()
    
    rowsQuery = """SELECT DC_ID, DIST_COST FROM supplier;"""
    cur.execute(rowsQuery)
    numberOfRows = cur.fetchall()
    
    store = []
    tempCost = []
    
    for row in numberOfRows:
        tempCost.append(row[1])
        store.append(row[0].replace(" ",""))
        
    
    distributor_cost = dict(zip(store, tempCost))

    # creating a dictionary that has the distributors and the weekly capacity for each
    # supplier capacity constraint #####
    dominos_db = "dominos_db.sqlite"
    conn = sqlite3.connect(dominos_db)
    cur = conn.cursor()
    
    rowsQuery = """SELECT DC_ID, SUPPLY_CAPACITY FROM supplier;"""
    cur.execute(rowsQuery)
    numberOfRows = cur.fetchall()
    
    store = []
    capacity = []
    
    for row in numberOfRows:
        capacity.append(float(row[1].replace(',','')))
        store.append(row[0].replace(" ",""))
    
        
    distributor_capacity = dict(zip(store, capacity))
    
    conn.close()

    
    # solving problem 3 ##################################################################
    dominos = Model()
    mix = {}
    for distributor in distributors:
        for store in stores:
            mix[distributor, store] = dominos.addVar(vtype = GRB.CONTINUOUS,
                                                   name = distributor + '_' +
                                                   str(store))
    dominos.update()
    
    # constraints 
    # distributor capacity
    dominosConstr = {}
    for distributor in distributors:
        constrName = "capacity_" + distributor
        dominosConstr[constrName] = dominos.addConstr(quicksum(mix[distributor, store] 
                                                    for store in stores) 
                                                    <= distributor_capacity[distributor],
                                                     name = constrName)
    
    # store demand    
    for store in stores:
        constrName = "demand_" + str(store)
        dominosConstr[constrName] = dominos.addConstr(quicksum(mix[distributor, store]
                                                    for distributor in distributors) >=
                                                     store_demand[store],
                                                     name = constrName)
            
    dominos.update()
    
                                           
    # the cost per mile * fraction of truckload * 2 (for trip there and back)
    obj = quicksum((mix[distributor, store]/9000) * 2 * distributor_cost[distributor] *
                   store_dist[distributor, store] for distributor in distributors
                   for store in stores)
    
    dominos.setObjective(obj, GRB.MINIMIZE)
    dominos.update()
    
    dominos.write('dominos.lp')
    dominos.optimize()
    dominos.write('dominos.sol')
    
    # creating a table in the database with the solution information
    mySolList = []
    for (k1, k2), n in mix.items():
        if n.x > 0:
            mySolList.append((k1,k2,n.x))
            
         
    dominos_db = "dominos_db.sqlite"
    conn = sqlite3.connect(dominos_db)
    cur = conn.cursor()  
    
    cur.execute("PRAGMA TABLE_INFO(p3_solution);")
    if len(cur.fetchall()) == 0:
        creatSolTable = """CREATE TABLE p3_solution
                            (DISTRIBUTION_CENTER text,
                            STORE integer,
                            DOUGHS real);"""
                            
        cur.execute(creatSolTable)
        conn.commit()
        cur.executemany("INSERT INTO p3_solution VALUES(?, ?, ?);", mySolList)
        conn.commit()
        conn.close()
        print("\np3_solution table created")
    
    else:
        print("\np3_solution already exists")
        conn.close()
        
print("\nUse function problem3() to run problem 3")


if __name__ == "__main__":
    print("\nStarting problem 1 ---------------------------")
    problem1()
    print("\nStarting problem 3 ---------------------------")
    problem3()