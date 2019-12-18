# Nick Newman Homework10

import multiprocessing as mp 
import traceback
import random
import time
import gurobipy as grb
import csv        
from colorama import init, Fore, Back, Style
init(convert=True)

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

# this is the routine that is parallelized
def varProbe(input_queue, output_queue, start_time):
    filepath = "handler.lp"
    NFLR = grb.read(filepath)
    NFLR.setParam('TimeLimit',15)
    NFLR.setParam('LogToConsole',0)
    NFLR.setParam('THREADLIMIT',1)

    while True:
        try:
            task = input_queue.get()
            try: 
                if task[0] is None:
                    break
                myVar = NFLR.getVarByName('GO_' + '_'.join(list(task)))
                myVar.lb = 1
                NFLR.update()
                NFLR.optimize()
                if NFLR.status == grb.GRB.INFEASIBLE:
                    myVar.lb, myVar.ub = 0,0
                    mymessage = "infeasible"
                    
                else:
                    myVar.lb = 0
                    mymessage = "good"
                NFLR.update()
                output_queue.put((1, task, mymessage))
            except:
                output_queue.put((2, task, traceback.format_exc()))
        except:
            time.sleep(2)
         
    return


# this routine is the one that preps, manages, and terminates the parallel process
def myHandler(free_vars, var_status, NFL, pool_size, start_time):

    def populate(free_vars, input_queue):
        counter = 0
        for v in free_vars:
            if free_vars[v].UB != free_vars[v].LB:
                input_queue.put(v)
                counter += 1
        return counter

    NFL.write('handler.lp')
    stop = False
    run = 0
    while not stop:
        run += 1
        print('\nCOMPLETING RUN NUMBER {}'.format(run))
        input_queue = mp.Queue()
        output_queue = mp.Queue()
        stop = True
        count = populate(free_vars, input_queue)
        print("Number in queue: ",count)
        print('(MASTER): COMPLETED LOADING QUEUE WITH TASKS WITH A TOTAL RUN TIME OF {}'.format(time.mktime(time.localtime())-time.mktime(start_time)))
        
        for i in range(pool_size*2):
            input_queue.put((None, None))
        print('(MASTER): COMPLETED LOADING QUEUE WITH NONES WITH A TOTAL RUN TIME OF {}'.format(time.mktime(time.localtime())-time.mktime(start_time)))  
        my_processes = [mp.Process(target=varProbe, args=(input_queue, output_queue, start_time)) for _ in range(pool_size)]
        
        for p in my_processes:
            p.start()
            
        counter = 0
        
        while counter < count:
            try: 
                result = output_queue.get()
                            
                try:
                    if result[0] == 1:
                        counter += 1
                        running_time = time.mktime(time.localtime())-time.mktime(start_time)
                        my_message = result[1]
                        status = result[2]
                        if 'infeasible' in status:
                            stop = False
                            var_status[my_message] = (0,0)
                            free_vars[my_message].LB = 0
                            free_vars[my_message].UB = 0
                            NFL.update()
                            print(str(counter) + "/"+ str(count), my_message, "---->", status, "TIME:",running_time)
                        else:
                            print(Fore.BLACK + Back.GREEN + str(counter)+ "/"+ str(count), my_message, "---->", status, "TIME:",running_time, Style.RESET_ALL)
                        
                    elif result[0] == 0:
                        my_message = result[1]
                        print(str(counter) + "/"+ str(count), my_message, "---->", status, "TIME:",running_time)
                        
                    else:
                        print(result + '\n' + traceback.format_exc())
                except:
                    print(traceback.format_exc())
                                    
            except:
                time.sleep(1)
                
        NFL.write('handler.lp')
        

        for p in my_processes:
            p.join()
        for p in my_processes:
            p.terminate()
        
        number_tasks = output_queue.qsize()
        for i in range(number_tasks):
            print(output_queue.get_nowait()[1])
            
        
        number_tasks = input_queue.qsize()
        for i in range(number_tasks):
            try:
                input_queue.get_nowait()
            except:
                pass
        
        print('(MASTER): COMPLETED FLUSHING QUEUE WITH A TOTAL RUN TIME OF {}'.format(time.mktime(time.localtime())-time.mktime(start_time)))
    
    return
    
if __name__ == "__main__":
    main()