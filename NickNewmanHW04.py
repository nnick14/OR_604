## Nick Newman Homework 04 ###############################################3
import sqlite3
import os
import csv
from gurobipy import *
from math import ceil


def problem1():

    filepath = os.path.dirname(__file__)
    
    fileArdent = open(os.path.join(filepath, "Ardent_Mills_Data.csv"), "rt")
    fileDemand = open(os.path.join(filepath, "average_daily_demand.csv"), "rt")
    fileDistributor = open(os.path.join(filepath, "Distributor_Data.csv"), "rt")
    
    ArdentReader = csv.reader(fileArdent)
    next(ArdentReader)
    DemandReader = csv.reader(fileDemand)
    next(DemandReader)
    DistributorReader = csv.reader(fileDistributor)
    next(DistributorReader)
    
    pizza_db = "pizza_db.sqlite"
    conn = sqlite3.connect(pizza_db)
    cur = conn.cursor()
    
    cur.execute("""DROP TABLE IF EXISTS ardent;""")
    cur.execute("""DROP TABLE IF EXISTS demand;""")
    cur.execute("""DROP TABLE IF EXISTS distributor;""")
    
    createArdent = """CREATE TABLE ardent
                        (STORE text,
                        LATITUDE real,
                        LONGITUDE real,
                        SUPPLY_CAPACITY integer,
                        UNIT_COST real);"""
                        
    createDemand = """CREATE TABLE demand
                        (STOREID integer,
                        AVG_DEMAND integer,
                        DIST_CENTER text);"""
                        
    createDistributor = """CREATE TABLE distributor
                            (DIST_ID text,
                            ADDRESS text,
                            LATITUDE real,
                            LONGITUDE real,
                            SUPPLY_CAPACITY integer,
                            MILE_COST real);"""
                            
    cur.execute(createArdent)
    cur.execute(createDemand)
    cur.execute(createDistributor)
    conn.commit()
    
    
    tempList = []
    for row in ArdentReader:
        tempList.append([row[0].replace(' ',''), row[1], row[2], row[3], row[4]])
    cur.executemany('INSERT INTO ardent VALUES(?,?,?,?,?);', tempList)
    conn.commit()
    
    tempList = []
    for row in DemandReader:
        tempList.append([row[0], row[1], row[2]])
    cur.executemany('INSERT INTO demand VALUES(?,?,?);', tempList)
    conn.commit()
    
    tempList = []
    for row in DistributorReader:
        tempList.append([row[0].replace(' ',''), row[1], row[2], row[3], row[4], row[5]])
    cur.executemany('INSERT INTO distributor VALUES(?,?,?,?,?,?);', tempList)
    conn.commit()
    
    
    fileArdent.close()
    fileDemand.close()
    fileDistributor.close()
    
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
    
    
    ### average demand by dist center in number of doughs per week 
    # Converted it to weekly by multiplying the sum of averages for each distribution
    # center by 7.
    # This was converted to pounds: 3.25 C of flour in each pizza dough, a pound of
    # all purpose flour is 3.25 C. This means that each dough is 1 lb
    cur.execute("""SELECT SUM(AVG_DEMAND)*7, DIST_CENTER FROM demand
                GROUP BY DIST_CENTER;""")
    
    Query = cur.fetchall()
    demand = {}
    for row in Query:
        demand[row[1]] = row[0]
    
    
    ### creating a haversine distance function
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
    
    ### creating a dictionary with the keys being the names of the mills and  
    #   distributors and the values being the distance between the two in miles
    cur.execute("""SELECT w.STORE, d.DIST_ID, w.LATITUDE, w.LONGITUDE, d.LATITUDE, 
                d.LONGITUDE FROM ardent w, distributor d;""" )           
    Query = cur.fetchall()
    
    miles = {}
    for row in Query:
        ID = (row[0], row[1])
        distance = haversine(row[3], row[2], row[5],row[4], "mi")
        miles[ID] = distance
        
    
    ### supply/capacity in 50lb bags of dough/week for each mill
    # this was converted to lbs by multiplying each by 50
    cur.execute("""SELECT STORE, SUPPLY_CAPACITY FROM ardent;""")
    Query = cur.fetchall()
    
    supply = {} 
    for row in Query:
        supply[row[0]] = int(row[1].replace(',',''))*50
    
    
    ### distance cost dictionary cost for trucks per mile traveled 
    cur.execute("""SELECT DIST_ID, MILE_COST FROM distributor;""")
    Query = cur.fetchall()
    
    distance_cost = {}
    for row in Query:
        distance_cost[row[0]] = row[1]
        
    
    
    ### distribution centers 
    cur.execute("""SELECT DIST_ID FROM distributor;""")
    Query = cur.fetchall()
    
    dist_centers = []
    for row in Query:
        dist_centers.append(row[0])
        
    
    ### mills/warehouses 
    
    cur.execute("""SELECT STORE FROM ardent;""")
    Query = cur.fetchall()
    
    warehouses = []
    for row in Query:
        warehouses.append(row[0])
        
    
    ### unit cost 
    # cost per unit from each warehouse in dollars per pound of dough
    
    cur.execute("""SELECT STORE, UNIT_COST FROM ardent;""")
    Query = cur.fetchall()
    
    unit_cost = {}
    for row in Query:
        unit_cost[row[0]] = row[1]/50
        
    unit_cost
    
    ### operating cost of open factories 
    op_cost = 700000
    
    
    
    ### solving the problem in gurobi ###########################################
    ### variables
    pizza = Model()
    x = {} # 1 if warhouse serves distrubutor, else 0
    y = {} # 1 if warehouse is operating, else 0
    for warehouse in warehouses:
        y[warehouse] = pizza.addVar(vtype = GRB.BINARY,
                                     name = warehouse)
        
    for warehouse in warehouses:
        for dist in dist_centers:
            x[warehouse, dist] = pizza.addVar(vtype = GRB.BINARY,
                                                 name = warehouse + '_' + dist)
            
    pizza.update()
    
    ### constraints    
    pizzaConstr = {}
    for dist in dist_centers:
        constrName = "distLimit_" + dist
        pizzaConstr[constrName] = pizza.addConstr(quicksum(x[warehouse, dist] for
                                                       warehouse in warehouses) == 1,
                                                        name = constrName)           
    
    for warehouse in warehouses:
        constrName = "supply_" + warehouse
        pizzaConstr[constrName] = pizza.addConstr(quicksum(x[warehouse, dist] * demand[dist] for
                                   dist in dist_centers) <= supply[warehouse] * y[warehouse],
                                    name = constrName)
         
    pizza.update()   
    
    ### objective function
    # truck capacity is 44,000 lbs and they have to go to and from the distribution center
    # finding the operating cost, distance traveled cost, and cost per unit
    obj = quicksum(op_cost * y[warehouse] + quicksum(miles[warehouse, dist] * x[warehouse, dist] * ceil(demand[dist]/44000)
            * 2 * distance_cost[dist] + unit_cost[warehouse] * demand[dist] * x[warehouse, dist] for dist in dist_centers)
                     for warehouse in warehouses)
                
    pizza.setObjective(obj, GRB.MINIMIZE)            
    pizza.update()
    
    
    pizza.write('pizza.lp')
    pizza.optimize()
    pizza.write('pizza.sol')
    
    ### solution list
    mySolList = []
    for (k1, k2), n in x.items():
        if n.x > 0:
            mySolList.append((k1,k2,n.x))
            
    for k, v in y.items():
        if v.x > 0:
            mySolList.append((k,v.x))
    
    ### entering it into the database
            
    pizza_db = "pizza_db.sqlite"
    conn = sqlite3.connect(pizza_db)
    cur = conn.cursor()
    
    cur.execute("PRAGMA TABLE_INFO (mill_dist);")
    if len(cur.fetchall()) == 0:
        cur.execute("""CREATE TABLE mill_dist
                        (WAREHOUSE text,
                        DIST_CENTER text,
                        STATUS integer);""")
        conn.commit()
        cur.executemany("INSERT INTO mill_dist VALUES(?,?,?);", mySolList[:16])
        conn.commit()
        print("\nmill_dist table created") 
    else:
        print("\nmill_dist already exists")
        
        
    cur.execute("PRAGMA TABLE_INFO (open_warehouses);")    
    if len(cur.fetchall()) == 0:
        cur.execute("""CREATE TABLE open_warehouses
                        (WAREHOUSE text,
                        STATUS integer);""")
        conn.commit()
        cur.executemany("INSERT INTO open_warehouses VALUES(?,?);", mySolList[16:])
        conn.commit()
        conn.close()
        print("\nopen_warehouses table created")
    else:
        print("\nopen_warehouses already exists")
        conn.close()


print("\nUse function problem1() to run problem 1")


if __name__ == "__main__":
    print("\nStarting problem 1 ---------------------------")
    problem1()