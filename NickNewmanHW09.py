### Nick Newman Homework09

import gurobipy as grb
import csv
import time
import os

# Reading in the model file
NFL = grb.Model()
filepath = "OR604 Model File v2.lp"
#filepath = os.path.join(os.path.dirname(__file__), "OR604 Model File v2.lp")
NFL = grb.read(filepath)
NFL.setParam('TimeLimit',10)
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
                print(row.getVar(r).varName)
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
            
#%%
# Running through the variables and updating them
## Took about 6.5 hours to run #######################
start = time.time()
NFL.setParam('TimeLimit',10)
stop=False
# run until this iterates through all variables without being infeasible
while not stop:
    stop=True
    count = 0
    for v in free_vars:
        # adding a count to more clearly see where the function is in the list
        # of variables
        count+= 1
        # if the variable is already set to 1 or 0 then skip it
        if v in set_vars or free_vars[v].UB == 0:
            continue
        # fix the variable lower bound to 1
        free_vars[v].LB = 1
        NFL.update()
        print("This is the count -------> ",count)
        NFL.optimize()
        # if the model is infeasible then fix it to 0 and rerun the model with
        # the changed bounds
        if NFL.status == grb.GRB.INFEASIBLE:
            # if the model has changed bounds this is set to False in order
            # to repeat until nothing changes
            stop = False
            var_status[v] = (0,0)
            free_vars[v].LB = 0
            free_vars[v].UB = 0
            zero_bound_vars.append(v)
        # if the model is feasible, continue iterating through the variables
        else:
            free_vars[v].LB = 0
            
        NFL.update()
        
    NFL.write('NFL_completed.lp')
    with open('NFL_variables_nonzero.csv','w',newline="") as myfile:
    writer = csv.writer(myfile, delimiter=',')
    writer.writerow(['Variable','Lower_Bound','Upper_Bound'])
    for v in free_vars:
        writer.writerow([v,free_vars[v].LB,free_vars[v].UB])

# setting those skipped variables to 0 in the var_status        
for v in var_status:
    if v in zero_bound_vars:
        var_status[v] = (0,0)
NFL.update()
end = time.time()
print("Time Elapsed: ", end-start)

# writing the model with the fixed bounds
NFL.write('NFL_completed.lp')

# deleting the zero bound variables from free_vars
for v in zero_bound_vars:
    if v in free_vars:
        del free_vars[v]
        
# creating csv with nonzero variables
with open('NFL_variables_nonzero.csv','w',newline="") as myfile:
    writer = csv.writer(myfile, delimiter=',')
    writer.writerow(['Variable','Lower_Bound','Upper_Bound'])
    for v in free_vars:
        writer.writerow([v,free_vars[v].LB,free_vars[v].UB])

# csv with zero bound variables        
with open('NFL_variables_zero.csv','w',newline="") as myfile:
    writer = csv.writer(myfile, delimiter=',')
    writer.writerow(['Variable'])
    for v in zero_bound_vars:
        writer.writerow([v])

# csv with all variables        
with open('NFL_var_and_zero.csv','w',newline="") as myfile:
    writer = csv.writer(myfile, delimiter=',')
    writer.writerow(['Variable','Lower_Bound','Upper_Bound'])
    for v in free_vars:
        writer.writerow([v,free_vars[v].LB,free_vars[v].UB])
    for v in zero_bound_vars:
        writer.writerow([v, 0, 0])

