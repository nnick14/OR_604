# Nick Newman Homework11

import multiprocessing as mp 
import traceback
import random
import time
import gurobipy as grb
import csv        
from termcolor import colored
from colorama import init, Fore, Back
init()

# setting up the main parameters for the model
# reading in the NFL lp file and filtering out all variables that can be 
# pre-contstrained to 0
def main(pool_size=4):
    
    #setting the start time
    start_time = time.localtime()
    filepath = "OR604 Model File v2.lp"
    NFL = grb.read(filepath)
    myVars = NFL.getVars()
    
    
    # saving the games variables in a games dictionary
    games = {}
    for v in myVars:
        if v.varName[:2] == 'GO':
            games[v.varName] = v
            
    # saving variable names and bounds into dictionaries
    free_vars = {}
    var_status = {}
    for v in myVars:
        if v.varName[:2] == 'GO':
            temp = v.varName.split('_')
            if 'PRIME' in temp:
                free_vars[tuple(temp[1:])] = v
                var_status[tuple(temp[1:])] = (v.LB,v.UB)

            
    # find all variables that can automatically be fixed to 0
    # this takes into account the contraints that contain penalty variables
    # and can't be fixed to 0     
    myConstrs = NFL.getConstrs()
    for c in myConstrs:
        if c.sense == '<' and c.RHS == 0:
            row = NFL.getRow(c)
            PenaltyVar = False
            for r in range(row.size()):
                if 'GO' not in row.getVar(r).varName:
                    PenaltyVar = True
            if not PenaltyVar:
                for r in range(row.size()):
                    row.getVar(r).LB = 0
                    row.getVar(r).UB = 0
    NFL.update()
    
    # deleting variables with 0 UB and 0 LB and adding them to a list full of 
    # zero bounds variables
    zero_bound_vars = []
    for v in var_status:
        if free_vars[v].UB == 0 and free_vars[v].LB ==0:
            if v in free_vars:
                zero_bound_vars.append(v)
                del free_vars[v]
                
    # list with variables that have 1 UB and 1 LB
    set_vars = []
    for v in var_status:
        if var_status[v][0] == 1.0 and var_status[v][1] == 1.0:
            set_vars.append(v)
                

    
    my_seed = 12345
    random.seed(my_seed)
    
    myHandler(free_vars, var_status, NFL, pool_size, start_time)
    
    NFL.write('NFL_completed.lp')
    with open('NFL_variable_bounds.csv','w',newline="") as myfile:
        writer = csv.writer(myfile, delimiter=',')
        writer.writerow(['Variable','Lower_Bound','Upper_Bound'])
        for v in free_vars:
            writer.writerow([v,free_vars[v].LB,free_vars[v].UB])
        
    print('(MASTER):  ALL PROCESSES HAVE COMPLETED WITH A TOTAL RUN TIME OF {}'.format(time.mktime(time.localtime())-time.mktime(start_time)))
      
    return