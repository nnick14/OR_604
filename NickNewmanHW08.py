### Nick Newman
### NFL Problem Homework 08
from gurobipy import *
import csv
import os
import sqlite3
from collections import defaultdict

def Homework08():
    filepath = os.path.dirname(__file__)
    fileGame = open(os.path.join(filepath, "GAME_VARIABLES_2018_V1.csv"),"rt")
    fileTeam = open(os.path.join(filepath, "TEAM_DATA_2018_v1.csv"), "rt")
    fileOpponents = open(os.path.join(filepath, "opponents_2018_V1.csv"),"rt")
    fileNetwork = open(os.path.join(filepath, "NETWORK_SLOT_WEEK_2018_V01.csv"),"rt")
    
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
                 season.select(t,'*',17,'*','*') if teams[t][0:2]!=teams[h][0:2]) == 0,
                name=cName)
        
    ## Constraint 20
    for t in teams:
        for w in range(1,16):
            cName = "20_THUN_1_time_zone_{}_{}".format(t, w)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in
                     season.select(t,'*',w,thursday_slots,'*') if abs(teams[t][2]-teams[h][2]) >=2) == 0,
                name=cName)
                
    ## Constraint 21
    bye_gms = {}
    for h in teams:
        for a in home_teams[h]:
            for w in range(5,13):
                bye_gms[h,a,w] = NFL.addVar(vtype = GRB.BINARY, obj=0,
                       name = h+a+str(w))
    NFL.update()

    for t in teams:
        for h in away_teams[t]:
            for w in range(5,13):
                cName = "21_teams_off_bye_{}_{}_{}".format(t,h,w)
                NFLConstr[cName] = NFL.addConstr(games[h,'BYE',w-1,'SUNB','BYE'] + quicksum(games[t,h,w,s,n] for [t,h,w,s,n] in 
                         season.select(t,h,w,'*','*')) <= 1 + bye_gms[h,t,w],
                    name = cName)
          
        cName = "Link21_{}".format(t)
        NFLConstr[cName] = NFL.addConstr(quicksum(bye_gms[h,t,w] for h in away_teams[t] for w in range(5,13)) <= 2,
                 name = cName)
                

    ## Constraint 22a
    div_games = []
    for t1 in teams:
        for t2 in home_teams[t1]:
            if teams[t1][0:2] == teams[t2][0:2]:
                if (t1,t2) not in div_games and (t2,t1) not in div_games:
                    div_games.append((t1,t2))

    for (t1,t2) in div_games:
        if teams[t1][0:2]==teams[t2][0:2]:
            for w in range(1,17):
                wk = [w,w+1]
                cName = "22a_division_back_{}_{}_{}".format(t1,t2,w)
                NFLConstr[cName] = NFL.addConstr(quicksum(games[t1,t2,w,s,n] for t1,t2,w,s,n in
                     season.select(t1,t2,wk,'*','*')) +
            quicksum(games[t2,t1,w,s,n] for t2,t1,w,s,n in season.select(t2,t1,wk,'*','*')) <= 1,
            name = cName)


    ## Constraint 22b
    for (t1,t2) in div_games:
        if teams[t1][0:2]==teams[t2][0:2]:
            for w in range(1,17):
                cName = "22b_division_back_bye_{}_{}_{}".format(t1,t2,w)
                NFLConstr[cName] = NFL.addConstr(quicksum(2*games[t1,t2,w,s,n] for t1,t2,w,s,n in
                     season.select(t1,t2,[w,w+2],'*','*')) +
            quicksum(2*games[t2,t1,w,s,n] for t2,t1,w,s,n in season.select(t2,t1,[w,w+2],'*','*')) +
                    quicksum(games[t1,h,w,s,n] for [t1,h,w,s,n] in season.select(t1,'BYE',w+1,'*','*')) +
                    quicksum(games[t2,h,w,s,n] for [t2,h,w,s,n] in season.select(t2,'BYE',w+1,'*','*')) <= 4,
            name = cName)
            
    
    ## Constraint 23
    Pen23 = {}

    for t in teams:
        Pen23[t] = NFL.addVar(vtype=GRB.BINARY, obj=-2,name="Pen23_{}".format(t))
        cName = "Constr_Pen23_{}".format(t)
        NFLConstr[cName] = NFL.addConstr(Pen23[t] <= 1, name=cName)
        for i in range(4,15):
            wk = [x for x in range(i,i+3)]
            cName = "23_no_three_away_{}_{}".format(t, i)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'*',wk,'*','*')) <= 2 + Pen23[t],
                     name = cName)
            cName = "23_no_three_home_{}_{}".format(t, i)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[a,t,w,s,n] for a,t,w,s,n in season.select('*',t,wk,'*','*')) <= 2 + Pen23[t],
                     name = cName)
            
    
    ## Constraint 24
    Pen24 = {}
    net = ['ESP','CBS','FOX','NBC','INT','NFL']
    for t in teams:
        Pen24[t] = NFL.addVar(vtype=GRB.BINARY, obj=-1,name="Pen24_{}".format(t))
        for w in range(1,17):
            cName = "24_consecutive_1_time_zone_{}_{}".format(t, w)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in
                     season.select(t,'*',w,'*',net) if abs(teams[t][2]-teams[h][2]) >=2) +
                quicksum(games[t,h,w,s,n] for t,h,w,s,n in
                     season.select(t,'*',w+1,'*',net) if abs(teams[t][2]-teams[h][2]) >=2) <= 1 + Pen24[t],
                name=cName)
                

    ## Constraint 25
    Pen25 = {}
    for t in teams:
        Pen25[t] = NFL.addVar(vtype=GRB.BINARY, obj=-5,name="Pen25_{}".format(t))
        wk = [1,2]
        cName = "25_no_two_open_away_{}".format(t)
        NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'*',wk,'*','*')) <= 1 + Pen25[t],
                 name = cName)


    ## Constraint 26
    Pen26 = {}        
    for t in teams:
        Pen26[t] = NFL.addVar(vtype=GRB.BINARY, obj=-3,name="Pen26_{}".format(t))
        wk = [16,17]
        cName = "26_no_two_end_away_{}".format(t)
        NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'*',wk,'*','*')) <= 1 + Pen26[t],
                 name = cName)
    

    
    ## Constraint 27
    FL_teams = ['MIA','JAC','TB']
    Pen27 = {}    
    for t in FL_teams:
        for w in range(1,5):
            Pen27[t,w] = NFL.addVar(vtype=GRB.BINARY, obj=-1,name="Pen27_{}_{}".format(t,w))
            cName = "27_no_early_FL_home_{}_{}".format(t,w)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[a,t,w,s,n] for a,t,w,s,n in season.select('*',t,w,'SUNE','*')) == 0 + Pen27[t,w],
                     name = cName)
    
    
    ## Constraint 28
    Pen28 = {}
    sun_slots = ['SUNE','SUNL','SUND']
    for n in ['CBS','FOX']:
        
        for w in range(1,18):
            Pen28[n,w] = NFL.addVar(vtype=GRB.BINARY, obj= -7,name="Pen28_{}_{}".format(n,w))
            cName = "28_no_less_than_5_games_{}_{}".format(n,w)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[a,h,w,s,n] for a,h,w,s,n in season.select('*','*',w,sun_slots,n)) >= 5 - Pen28[n,w],
                     name = cName)
        cName = "28PEN_no_less_than_5_games_{}".format(n)
        NFLConstr[cName] = NFL.addConstr(quicksum(Pen28[n,w] for w in range(1,18)) <= 1, name=cName) 

    ## Constraint 29
    Pen29 = {}
    wk = [w for w in range(1,18)]
    sun_slots = ['SUNE','SUNL','SUND']
    for (t1, t2) in div_games:
        Pen29[t1,t2] = NFL.addVar(vtype=GRB.BINARY, obj= -10,name="Pen29_{}_{}".format(t1,t2))
        cName = "29_CBS_FOX_divisional_games_{}_{}".format(t1,t2)
        if teams[t1][0] == 'NFC':
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t1,t2,w,s,n] for t1,t2,w,s,n in season.select(t1,t2,wk,sun_slots,'FOX'))
            >= 1 - Pen29[t1,t2])
        
        else:
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t1,t2,w,s,n] for t1,t2,w,s,n in season.select(t1,t2,wk,sun_slots,'CBS'))
            >= 1 - Pen29[t1,t2])
    
    ## Constraint 30
    Pen30 = {}
    for (t1,t2) in div_games:
        Pen30[t1,t2] = NFL.addVar(vtype=GRB.BINARY, obj=-8,name="Pen30_{}_{}".format(t1,t2))
        if teams[t1][0:2]==teams[t2][0:2]:
            wk = [w for w in range(1,10)]
            cName = "30_division_first__half_{}_{}".format(t1,t2)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t1,t2,w,s,n] for t1,t2,w,s,n in
                 season.select(t1,t2,wk,'*','*')) +
            quicksum(games[t2,t1,w,s,n] for t2,t1,w,s,n in season.select(t2,t1,wk,'*','*')) <= 1 + Pen30[t1,t2],
            name = cName)
                
    ## Constraint 31
    Pen31 = {}
    for t in teams:
        for w in range(1,15):
            Pen31[t,w] = NFL.addVar(vtype=GRB.BINARY, obj= -3,name="Pen31_{}_{}".format(t,w))
            cName = "31_no_road_after_MONN_{}_{}".format(t,w)
            NFLConstr[cName] = NFL.addConstr(quicksum(games[t,h,w,s,n] for t,h,w,s,n in season.select(t,'*',w,'MONN','ESP'))+
                     quicksum(games[a,t,w,s,n] for a,t,w,s,n in season.select('*',t,w,'MONN','ESP')) +
                     quicksum(games[t,h,x,s,n] for t,h,x,s,n in season.select(t,'*',w+1,'*','*')) <= 1 + Pen31[t,w],
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
    print("\nStarting Homwork08 Problem -------------------------------------------")
    print("\nProblem takes a long time to run.")
    Homework08()