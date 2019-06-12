import math
from decimal import *

getcontext().prec = 10
class Error(Exception):
    """Base class for exceptions in this module."""
    pass

# Flattens a list of lists

def flatten(l):
    flat_list = [item for sublist in l for item in sublist]
    return flat_list

# Strips tab and comma delineators

def stripDelin(s):
    temp = s.replace('\t',' ').replace(',',' ')
    return temp

# convertLine(line_as_list as List,METER_FLAG as Boolean)
#   Replace coordinate line in a Crone PEM/STP file by incrementing by some displacement declared globally.
#   Precision can be edited by changing the argument of the .quantize methods.
#   Requires: List is at least of length 4

def convertLine(line_as_list,METER_FLAG):
    linelist = line_as_list
    if METER_FLAG:
        #Meters
        linelist[1] = str(Decimal((Decimal(linelist[1]) + Decimal(EASTdisplacementm))).quantize(Decimal('0.1')))
        linelist[2] = str(Decimal((Decimal(linelist[2]) + Decimal(NORTHdisplacementm))).quantize(Decimal('0.1')))
    else:
        #Feet
        linelist[1] = str(Decimal((Decimal(linelist[1]) + Decimal(EASTdisplacementm*3.28084))).quantize(Decimal('0.1')))
        linelist[2] = str(Decimal((Decimal(linelist[2]) + Decimal(NORTHdisplacementm*3.28084))).quantize(Decimal('0.1')))
    return linelist

def processFileGPS(FilePath,READONLY_FLAG,suffix):
    with open(FilePath) as f:
        lines = f.readlines()
    i = 0
    numEdits = 0
    while i < len(lines):
        edited_flag = False
        line = lines[i]
        line = line.strip('\n')
        if line != '' and line[0] =='<':
            flag = line[1]
            if flag == 'T' and line[1:4] != 'TXS' or flag == 'L' or flag == 'P':
                # Remove delineators
                templine = stripDelin(line)
                linelist = templine.split(' ')
                # Remove extra nullspace
                while '' in linelist: linelist.remove('')
                if len(linelist) < 5:
                    linelist = list(map(lambda x: x.split(","),linelist))
                    linelist = flatten(linelist)
                # Try converting line
                if len(linelist) > 1:
                    try: 
                        float(linelist[1]) and float(linelist[2])
                        if linelist[4] == '1': 
                            linelist = convertLine(linelist,False)
                        else: 
                            linelist = convertLine(linelist,True)
                        numEdits += 1
                        edited_flag = True
                    except ValueError:
                        pass
                    linelist.append('\n')
                    lines[i] = " ".join(linelist)
        if not edited_flag: line = line + '\n'
        i+=1
    print(FilePath + ": " + str(numEdits) + " line edits")

    NEW_PATH = FilePath
    if READONLY_FLAG:
        NEW_PATH = FilePath[0:len(FilePath)-4] + suffix + FilePath[len(FilePath)-4:len(FilePath)]
    with open(NEW_PATH,'w') as f:
        f.writelines(lines)
	