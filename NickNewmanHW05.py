## Nick Newman Homework 05 #############################################
from gurobipy import *
import csv
import os
import sqlite3

def problem1():
    filepath = os.path.dirname(__file__)
    fileDemand = open(os.path.join(filepath, "demand_price.csv"),"rt")
    fileFeedstock = open(os.path.join(filepath, "feedstock.csv"), "rt")
    fileProduction = open(os.path.join(filepath, "production.csv"),"rt")
    
    readDemand = csv.reader(fileDemand)
    next(readDemand)
    readFeedstock = csv.reader(fileFeedstock)
    next(readFeedstock)
    readProduction = csv.reader(fileProduction)
    next(readProduction)
    
    cows_db = "cows_db.sqlite"
    conn = sqlite3.connect(cows_db)
    cur = conn.cursor()
    
    cur.execute("""DROP TABLE IF EXISTS demand;""")
    cur.execute("""DROP TABLE IF EXISTS feedstock;""")
    cur.execute("""DROP TABLE IF EXISTS production;""")
    
    cur.execute("""CREATE TABLE demand
                    (MONTH integer,
                    DEMAND_GAL integer,
                    PRICE real);""")
    
    cur.execute("""CREATE TABLE feedstock
                (CALV_MONTH integer,
                FEED_COST real);""")
    
    cur.execute("""CREATE TABLE production
                (CALV_MONTH integer,
                JAN real,
                FEB real,
                MAR real,
                APR real,
                MAY real,
                JUN real,
                JUL real,
                AUG real,
                SEP real,
                OCT real,
                NOV real,
                DEC real);""")
    
    conn.commit()
    
    tempList = []
    for row in readDemand:
        tempList.append([row[0],row[1],row[2]])
    cur.executemany("INSERT INTO demand VALUES (?,?,?);", tempList)
    conn.commit()
    
    tempList = []
    for row in readFeedstock:
        tempList.append([row[0],row[1]])
    cur.executemany("INSERT INTO feedstock VALUES (?,?);", tempList)
    conn.commit()
    
    tempList = []
    for row in readProduction:
        tempList.append([row[0],row[1],row[2],row[3], row[4],row[5],row[6],row[7],row[8],row[9],
                        row[10],row[11],row[12]])
    cur.executemany("INSERT INTO production VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?);", tempList)
    conn.commit()
    
    fileDemand.close()
    fileProduction.close()
    fileFeedstock.close()
    
    
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
    
    
    ### creating demand and price dictionaries
    cur.execute("SELECT * FROM demand;")
    Query = cur.fetchall()
    demand = {}
    price = {}
    for row in Query:
        demand[row[0]] = row[1]
    for row in Query:
        price[row[0]] = float(row[2].split("$")[1])
    
    ### creating feed cost dictionary
    cur.execute("SELECT * FROM feedstock;")
    Query = cur.fetchall()
    
    cost = {}
    for row in Query:
        c = row[1].split
        cost[row[0]] = float(row[1].split("$")[1])
    
    ### creating production dictionary
    # first number is the calving month, second number is the demand month
    cur.execute("SELECT * FROM production;")
    Query = cur.fetchall()
    production = {}
    for row in Query:
        for i in range(1,13):
            production[(row[0],i)] = row[i]
    
    
    ### calving and demand month lists
    calving_month = list(range(1,13))
    demand_month = list(range(1,13))

   
    ### solving the homework problem in gurobi ######################################
    cow = Model()
    global cows
    cows = {}
    shortage = {}
    excess = {}
    for c in calving_month:
        cows[c] = cow.addVar(vtype = GRB.INTEGER,
               name = "calve_" + str(c)) 
       
    for d in demand_month:
        excess[d] = cow.addVar(vtype = GRB.INTEGER,
           name = "excess_" + str(d))
        
    for d in demand_month:
        shortage[d] = cow.addVar(vtype = GRB.INTEGER,
           name = "shortage_" + str(d))
    
        
    cow.update()

    ### constraint
    cowConstr = {}
    for d in demand_month:
        cName = "demand_cap_" + str(d)
        cowConstr[cName] = cow.addConstr(quicksum(production[c, d] * cows[c] for c in calving_month) - excess[d] + shortage[d] == demand[d],
                 name = cName)
    
    cow.update()
    
    ### objective function
    obj = quicksum(cost[c] * cows[c] for c in calving_month) + quicksum(price[d] * shortage[d] for d in demand_month) + quicksum(price[d]*.2 * excess[d] for d in demand_month)
     
    cow.setObjective(obj, GRB.MINIMIZE)
    cow.update()    
    
    cow.write('cow.lp')
    cow.optimize()
    cow.write('cow.sol')

    ### solution list
    mySolList = []
    for k, v in cows.items():
        if v.x > 0:
            mySolList.append(("Calve Month" + str(k), v.x))
    for k, v in excess.items():
        if v.x > 0:
            mySolList.append(("Excess" + str(k), v.x))
    for k, v in shortage.items():
        if v.x > 0:
            mySolList.append(("Shortage" + str(k), v.x))
    print("\nSolution List:")
    print(mySolList)
    
    ### entering it into the database       
    cows_db = "cows_db.sqlite"
    conn = sqlite3.connect(cows_db)
    cur = conn.cursor()
    
    cur.execute("PRAGMA TABLE_INFO (solution);")
    if len(cur.fetchall()) == 0:
        cur.execute("""CREATE TABLE solution
                        (VARIABLE text,
                        NUMBER integer);""")
        conn.commit()
        cur.executemany("INSERT INTO solution VALUES(?,?);", mySolList)
        conn.commit()
        conn.close()
        print("\nsolution table created") 
    else:
        print("\nsolution table already exists")
        conn.close()
        
print("\nUse function problem1() to run problem 1")


if __name__ == "__main__":
    print("\nStarting problem 1 --------------------------------------------")
    problem1()