### Nick Newman
### NFL Problem Homework 07
from gurobipy import *
import csv
import os
import sqlite3
from collections import defaultdict

def Homework07():
    filepath = os.path.dirname(__file__)
    fileGame = open(os.path.join(filepath, "GAME_VARIABLES_2018_V1.csv"),"rt")
    fileTeam = open(os.path.join(filepath, "TEAM_DATA_2018_v1.csv"), "rt")
    fileOpponents = open(os.path.join(filepath, "opponents_2018_V1.csv"),"rt")
    fileNetwork = open(os.path.join(filepath, "NETWORK_SLOT_WEEK_2018_V1.csv"),"rt")
    
    readGame = csv.reader(fileGame)
    next(readGame)
    readTeam = csv.reader(fileTeam)
    next(readTeam)
    readOpponents = csv.reader(fileOpponents)
    next(readOpponents)
    readNetwork = csv.reader(fileNetwork)
    next(readNetwork)
    
    NFL_db = "NFL_db.sqlite"
    conn = sqlite3.connect(NFL_db)
    cur = conn.cursor()
    
    cur.execute("""DROP TABLE IF EXISTS game_variables;""")
    cur.execute("""DROP TABLE IF EXISTS team_data;""")
    cur.execute("""DROP TABLE IF EXISTS opponents;""")
    cur.execute("""DROP TABLE IF EXISTS network_slot;""")
    
    cur.execute("""CREATE TABLE game_variables
                    (AWAY_TEAM text,
                    HOME_TEAM text,
                    WEEK integer,
                    SLOT text,
                    NETWORK text,
                    QUAL_POINTS real);""")
    
    cur.execute("""CREATE TABLE team_data
                    (TEAM text,
                    CONF text,
                    DIV text,
                    TIMEZONE integer,
                    QUALITY real);""")
    
    cur.execute("""CREATE TABLE opponents
                    (HOME text,
                    AWAY text)""")
    
    cur.execute("""CREATE TABLE network_slot
                    (WEEK integer,
                    SLOT text,
                    NETWORK text);""")
    
    conn.commit()
    
    tempList = []
    for row in readGame:
        tempList.append([row[0], row[1], row[2], row[3], row[4], row[5]])
    cur.executemany("INSERT INTO game_variables VALUES (?,?,?,?,?,?);", tempList)
    conn.commit()
    
    tempList = []
    for row in readTeam:
        tempList.append([row[0], row[1], row[2], row[3], row[4]])
    cur.executemany("INSERT INTO team_data VALUES (?,?,?,?,?);", tempList)
    conn.commit()
    
    tempList = []
    for row in readOpponents:
        tempList.append([row[0], row[1]])
    cur.executemany("INSERT INTO opponents VALUES (?,?);", tempList)
    conn.commit()
    
    tempList = []
    for row in readNetwork:
        tempList.append([row[0], row[1], row[2]])
    cur.executemany("INSERT INTO network_slot VALUES (?,?,?);", tempList)
    conn.commit()
    
    fileGame.close()
    fileTeam.close()
    fileOpponents.close()
    fileNetwork.close()
    
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
    
    ## list of lists with all the game variable information and converting to a tuplelist
    cur.execute("SELECT * FROM game_variables;")
    Query = cur.fetchall()
    season = []
    for row in Query:
        season.append((row[0], row[1], row[2], row[3], row[4], row[5]))
        
    season_qual = tuplelist(season)
    
    
    ## creating a list with all the team names
    team_data = []
    cur.execute("SELECT * FROM team_data;")
    Query = cur.fetchall()
    
    for row in Query:
        team_data.append([row[0], row[1],row[2],row[3],row[4]])
    
    teams = defaultdict(list)
    for row in team_data:
        teams[row[0]] = [row[1],row[2],row[3],row[4]]
    
    
    ## creating dictionaries with the home and away team information
    #key is the away team and values are home team opponents
    away_teams = defaultdict(list)
    #key is the home team and values are the away team opponents
    home_teams = defaultdict(list)
    cur.execute("SELECT * FROM opponents;")
    Query = cur.fetchall()
    
    for row in Query:
        away_teams[row[0]].append(row[1])
        home_teams[row[1]].append(row[0])
    
    ## creating sets with the network and timeslot information
    cur.execute("SELECT * FROM network_slot;")
    Query = cur.fetchall()
    networks = []
    slots = []
    
    for row in Query:
        networks.append(row[2])
        slots.append(row[1])
        
    networks = set(networks)
    networks = list(networks)
    slots = set(slots)
    slots = list(slots)
    
    ## solving the homework problem in gurobi
    ## adding the games variable (away team, home team, week, timeslot, network)
    ## objective is quality
    NFL = Model()
    games = {}
    season_noqual = []
    for row in season_qual:
        a,h,w,s,n,q = row
        games[a,h,w,s,n] = NFL.addVar(vtype = GRB.BINARY, obj = q,
             name = a+h+str(w)+s+n)
        season_noqual.append((a,h,w,s,n))
        
    season = tuplelist(season_noqual)
    NFL.update()
    
    ## Constraint 1 
    NFLConstr = {}
    for t in teams:
        for h in away_teams[t]:
            cName = "01_matchup_once_{}_{}".format(t,h)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,h,'*','*','*')) ==1,
                     name=cName)
    
    ## Constraint 2 
    for t in teams:
        for w in range(1,18):
            cName = "02_each_team_one_game_{}_{}".format(t,w)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'*',w,'*','*')) + 
                     quicksum(games[a,t,w,s,n] for a,t,w,s,n in season.select('*',t,w,'*','*')) == 1,
                     name = cName)
            
           
    ## Constraint 3 
    bye_wks = range(4,13)
    for t in teams:
        cName = "03_bye_games_certain_wks_{}".format(t)
        NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'BYE',bye_wks,'SUNB','BYE')) == 1,
                 name=cName)
            
    ## Constraint 4 
    for w in bye_wks:
        cName = "04_lessthan_6_byes_wk_{}".format(w)
        NFLConstr[cName] = NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n in season.select('*','BYE',w,'SUNB','BYE')) <=6,
                 name=cName)
        
    ## Constraint 5 
    ## Miami and Tampa Bay are the two teams that had early byes in 2017
    for t in ['MIA','TB']:
        cName = "05_early_bye_{}".format(t)
        NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'BYE',4,'SUNB','BYE')) == 0,
                 name=cName)
        
    ## Constraint 6 
    ## One Thursday night game per week in weeks 1-15
    ## No Thursday night games in weeks 16 and 17
    ## The data doesn't have any THUN for weeks 16 or 17 so there's no need to do this
    for w in range(1,16):
        cName = "06_one_THUN_{}".format(w)
        NFLConstr[cName] = NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n in season.select('*','*',w,'THUN','*')) == 1,
                 name = cName)
    
    ## Constraint 7 
    ## One SatE and one SatL in weeks 15 and 16
    for w in range(15,17):
        for s in ['SATE','SATL']:
            cName = "07_SatGame_{}_{}".format(s,w)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n in season.select('*','*',w,s,'NFL')) == 1,
                     name = cName)
          
    ## Constraint 8a         
    for w in range(1,17):
        cName = "08a_one_doubleheader_{}".format(w)
        NFLConstr[cName] = NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n in season.select('*','*',w,'SUND','*')) == 1,
                 name = cName)
            
    ## Constraint 8b 
    ## CBS and FOX cannot have more than two double headers in a row
    for n in ['CBS','FOX']:
        for i in range(1,16):
            wk = [w for w in range(i, i+3)]
            cName = "08b_doubleheader_row_{}_{}_{}".format(n,i,i+2)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n in season.select('*','*',wk,'SUND',n)) <= 2,
                     name=cName)
            
    
    ## Constraint 8c 
    ## CBS and FOX each have a double header in week 17
    for n in ['CBS','FOX']:
        cName = "08c_week17_2doubleheaders_{}".format(n)
        NFLConstr[cName] = NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n in season.select('*','*',17,'SUND',n)) == 1,
                 name = cName)
        
    ## Constraint 9 
    ## one Sunday night game per week in weeks 1-16 and none in week 17  
    for w in range(1,17):
        cName = "09_one_SUNN_game_{}".format(w)
        NFLConstr[cName] = NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n in season.select('*','*',w,'SUNN','NBC')) == 1,
                 name=cName)
    
    ## Constraint 10a 
    ## there are two Monday night games in week one
    cName = "10a_two_MONN_1"
    NFLConstr[cName] = NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n in season.select('*','*',1,'MONN','ESP')) == 2,
             name = cName)
    
        
    ## Constraint 10b 
    ## the late Monday night game must be hosted by a west coast or mountain team
    west_coast = ['LAC','SF','SEA','OAK','LAR','DEN','ARI']
    cName = "10b_MONN_westcoast"
    NFLConstr[cName] = NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n in season.select('*',west_coast,1,'MONN','ESP')) == 1,
             name = cName)
    
    ## Constraint 10c
    ## there is only one Monday night game in weeks 1-16
    for w in range(2,17):
        cName = "10c_MONN_onegame_{}".format(w)
        NFLConstr[cName] = NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n in season.select('*','*',w,'MONN','ESP')) == 1,
                 name=cName)
        
    
    ## New Constraints
    thursday_slots = ['THUN','THUL','THUE']
    ## Constraint 11
    for t in teams:
        for i in range(1,15):
            wk = [x for x in range(i,i+4)]
            cName = "11_no_four_away_{}_{}".format(t, i)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'*',wk,'*','*')) <= 3,
                     name = cName)
            cName = "11_no_four_home_{}_{}".format(t, i)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[a,t,w,s,n] for a,t,w,s,n in season.select('*',t,wk,'*','*')) <= 3,
                     name = cName)
    
    ## Constraint 12
    for t in teams:
        for i in [1,2,3,15]:
            wk = [x for x in range(i,i+3)]
            cName = "12_no_three_away_{}_{}".format(t, i)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'*',wk,'*','*')) <= 2,
                     name = cName)
            cName = "12_no_three_home_{}_{}".format(t, i)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[a,t,w,s,n] for a,t,w,s,n in season.select('*',t,wk,'*','*')) <= 2,
                     name = cName)

    ## Constraint 13
    for t in teams:
        for i in range(1,13):
            wk = [x for x in range(i,i+6)]
            cName = "13_two_away_every_6wks_{}_{}".format(t, i)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'*',wk,'*','*')) >= 2,
                     name = cName)
            cName = "13_two_home_every_6wks_{}_{}".format(t, i)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[a,t,w,s,n] for a,t,w,s,n in season.select('*',t,wk,'*','*')) >= 2,
                     name = cName)
            
    ## Constrint 14
    for t in teams:
        for i in range(1,9):
            wk = [x for x in range(i,i+10)]
            cName = "14_four_away_every_10wks_{}_{}".format(t, i)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'*',wk,'*','*')) >= 4,
                     name = cName)
            cName = "14_home_every_10wks_{}_{}".format(t, i)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[a,t,w,s,n] for a,t,w,s,n in season.select('*',t,wk,'*','*')) >= 4,
                     name = cName)
            
    ## Constraint 15
    #### Per Dr. C. this is being omitted ####
    """
    for t in teams:
        for w in range(2,16):
            cName = "15_away_THUN_home_before_{}_{}".format(t,w)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in
                     season.select(t,'*',w,thursday_slots,'*')) + quicksum(games[t,h,x,s,n] for t,h,x,s,n in season.select(t,'*',w-1,'*','*')) <=1,
                name=cName)
    """
         
    ## Constraint 16
    for t in teams:
        for w in range(1,15):
            cName = "16a_no_THUN_after_MONN_{}_{}".format(t,w)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'*',w,'MONN','ESP'))+
                     quicksum(games[a,t,w,s,n] for a,t,w,s,n in season.select('*',t,w,'MONN','ESP')) +
                     quicksum(games[t,h,x,s,n] for t,h,x,s,n in season.select(t,'*',w+1,thursday_slots,'*')) +
                     quicksum(games[a,t,x,s,n] for a,t,x,s,n in season.select('*',t,w+1,thursday_slots,'*')) <= 1,
                     name=cName)
            
    for t in teams:
        for w in range(1,14):
            cName = "16b_no_THUN_two_after_MONN_{}_{}".format(t,w)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'*',w,'MONN','ESP'))+
                     quicksum(games[a,t,w,s,n] for a,t,w,s,n in season.select('*',t,w,'MONN','ESP')) +
                     quicksum(games[t,h,x,s,n] for t,h,x,s,n in season.select(t,'*',w+2,thursday_slots,'*')) +
                     quicksum(games[a,t,x,s,n] for a,t,x,s,n in season.select('*',t,w+2,thursday_slots,'*')) <= 1,
                     name=cName)
                                   
    ## Constraint 17
    for t in teams:
        for w in range(2,16):
            cName = "17_home_before_THUN_{}_{}".format(t, w)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in
                     season.select(t,'*',w,thursday_slots,'*')) + 
                quicksum(games[a,t,w,s,n] for a,t,w,s,n in season.select('*',t,w,thursday_slots,'*')) + 
                quicksum(games[t,h,x,s,n] for t,h,x,s,n in season.select(t,'*',w-1,'*','*')) <=1,
                name=cName)
                    
    ## Constraint 18
    for t in teams:
        for w in range(5,14):
            cName = "18_no_THUN_after_bye_{}_{}".format(t, w)
            NFLConstr[cName] = NFL.addConstr(games[t,'BYE',w-1,'SUNB','BYE'] +
                     quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'*',w, thursday_slots,'*'))+
                     quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select('*',t,w,thursday_slots,'*')) <= 1,
                              name=cName)
    
    ## Constraint 19
    for t in teams:
        cName = "19_wk17_division_{}".format(t)
        NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in
                 season.select(t,'*',17,'*','*') if teams[t][1]!=teams[h][1]) == 0,
                name=cName)
        
    ## Constraint 20
    for t in teams:
        for w in range(1,16):
            cName = "20_THUN_1_time_zone_{}_{}".format(t, w)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in
                     season.select(t,'*',w,thursday_slots,'*') if abs(teams[t][2]-teams[h][2]) >=2) == 0,
                name=cName)
    
    NFL.update()
    NFL.modelSense = GRB.MAXIMIZE
    NFL.update()
    
    NFL.write('NFL.lp')
    NFL.optimize()
    NFL.write('NFL.sol')
    
    mySolList = []
    for k,v in games.items():
        if v.x > 0:
            mySolList.append((k,v.x))
            
    mySol = []
    for i,j in mySolList:
        temp = []
        for a in i:
            temp.append(a)
        temp.append(j)
        mySol.append(temp)
        
    solution_db = "solution_db.sqlite"
    conn = sqlite3.connect(solution_db)
    cur = conn.cursor()
    
    cur.execute("PRAGMA TABLE_INFO (solution);")
    if len(cur.fetchall()) == 0:
        cur.execute("""CREATE TABLE solution
                        (AWAY_TEAM text,
                        HOME_TEAM text,
                        WEEK integer,
                        SLOT text,
                        NETWORK text,
                        STATUS integer);""")
        conn.commit()
        cur.executemany("INSERT INTO solution VALUES(?,?,?,?,?,?);", mySol)
        conn.commit()
        conn.close()
        print("\nsolution table created")
    else:
        print("\nsolution table already exists")
        conn.close()

print("\nUse function Homework07() to run the problem")
print("\nProblem takes about 40 minutes to run.")

if __name__ == "__main__":
    print("\nStarting Homwork07 Problem -------------------------------------------")
    print("\nProblem takes about 40 minutes to run.")
    Homework07()