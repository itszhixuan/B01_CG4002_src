## Currently, plan for 3 bluno data that detects motion
## Bluno 1: Right arm
## Bluno 2: Right leg
## Bluno 3: Left arm

## Plan is to compare 2 0.5s frames of data, and if any of the IMU data exceeds a certain threshold

## Data is sent in as an array of arrays
## Example Input (raw_data reflects the data from the first 0.5s frame)
## assuming 0.1s sends one set of data

###################################################################################################
# Updated start of move detection
# For collection of training data for MLP model training
# 3 blunos will be used to detect motion, as mentioned above
# However, feature extraction will not be done here in Bluno anymore compared to earlier version of startOfMove
# Will be done in Ultra96 after external comms recieves data, and processed before calling MLP script
###################################################################################################

import numpy as np
from scipy.stats import skew, kurtosis
import queue
import pandas as pd

collate_queue = queue.Queue() # used for collating data from the different bluno threads

def consumerThread():
    isFullCycleComplete = False # do not perform if one full iteration is complete
    isCollate = False # flag to determine if data should be collated
    # flags to determine if bluno has collected max samples for action
    isB1Complete = False
    isB2Complete = False
    isB3Complete = False
    # number of samples to collect after start of move has been detected
    max_iter = 80
    # data format: [time.time(), name, Ax, Ay, Az, Gx, Gy, Gz, seq_num]
    # arrays to store 80 samples
    bluno_1_collation_arr = []
    bluno_2_collation_arr = []
    bluno_3_collation_arr = []
    # arrays to store 5 samples
    bluno_1_prev_compare_arr = []
    bluno_2_prev_compare_arr = []
    bluno_3_prev_compare_arr = []
    bluno_1_curr_compare_arr = []
    bluno_2_curr_compare_arr = []
    bluno_3_curr_compare_arr = []
    while(not isFullCycleComplete): # while one full collation + output iteration is not complete
        if not isCollate:
            data = collate_queue.get()
            match data[1]:
                case "BLUNO_1":
                    if len(bluno_1_prev_compare_arr) < 5:
                        bluno_1_prev_compare_arr.append(data)
                    elif len(bluno_1_curr_compare_arr) < 5:
                        bluno_1_curr_compare_arr.append(data)
                    else:
                        # compare data
                        if isAboveThreshold(bluno_1_prev_compare_arr, bluno_1_curr_compare_arr):
                            isCollate = True # remember to clear the arrays !!!
                        else:
                            bluno_1_prev_compare_arr = bluno_1_prev_compare_arr[1:5]
                            bluno_1_prev_compare_arr.append(bluno_1_curr_compare_arr[0])
                            bluno_1_curr_compare_arr = bluno_1_curr_compare_arr[1:5]
                case "BLUNO_2":
                    if len(bluno_2_prev_compare_arr) < 5:
                        bluno_2_prev_compare_arr.append(data)
                    elif len(bluno_2_curr_compare_arr) < 5:
                        bluno_2_curr_compare_arr.append(data)
                    else:
                        # compare data
                        if isAboveThreshold(bluno_2_prev_compare_arr, bluno_2_curr_compare_arr):
                            isCollate = True # remember to clear the arrays !!!
                        else:
                            bluno_2_prev_compare_arr = bluno_2_prev_compare_arr[1:5]
                            bluno_2_prev_compare_arr.append(bluno_2_curr_compare_arr[0])
                            bluno_2_curr_compare_arr = bluno_2_curr_compare_arr[1:5]
                case "BLUNO_3":
                    if len(bluno_3_prev_compare_arr) < 5:
                        bluno_3_prev_compare_arr.append(data)
                    elif len(bluno_3_curr_compare_arr) < 5:
                        bluno_3_curr_compare_arr.append(data)
                    else:
                        # compare data 
                        if isAboveThreshold(bluno_3_prev_compare_arr, bluno_3_curr_compare_arr):
                            isCollate = True # remember to clear the arrays !!!
                        else:
                            bluno_3_prev_compare_arr = bluno_3_prev_compare_arr[1:5]
                            bluno_3_prev_compare_arr.append(bluno_3_curr_compare_arr[0])
                            bluno_3_curr_compare_arr = bluno_3_curr_compare_arr[1:5]
        else: # put all data into the collation queue
            bluno_1_collation_arr  = bluno_1_curr_compare_arr # initialise array with 5 values
            bluno_2_collation_arr  = bluno_2_curr_compare_arr 
            bluno_3_collation_arr  = bluno_3_curr_compare_arr 
            while(not isB1Complete): #or not isB2Complete or not isB3Complete):
                data = collate_queue.get()
                match data[1]:
                    case "BLUNO_1":
                        if len(bluno_1_collation_arr) < max_iter:
                            bluno_1_collation_arr.append(data)
                        else:
                            isB1Complete = True
                    case "BLUNO_2":
                        if len(bluno_2_collation_arr) < max_iter:
                            bluno_2_collation_arr.append(data)
                        else:
                            isB2Complete = True
                    case "BLUNO_3":
                        if len(bluno_3_collation_arr) < max_iter:
                            bluno_3_collation_arr.append(data)
                        else:
                            isB3Complete = True
            # send data to external comms
            # pub_queue.put(
            #     json.dumps(
            #         {
            #             "topic": "default",
            #             "payload": json.dumps(
            #                 {
            #                     "player_id": 1,
            #                     "action": "dummy",
            #                     "data": 
            #                         {
            #                             "BLUNO_1": bluno_1_collation_arr,
            #                             "BLUNO_2": bluno_2_collation_arr,
            #                             "BLUNO 3": bluno_3_collation_arr,
            #                         },
            #                 }
            #             ),
            #         }
            #     )
            # )
            # print(bluno_1_collation_arr) # test to print
            
            # write data collated into a csv
            # print(f"bluno 2 coll arr: {bluno_2_collation_arr}")
            csv_header_arr = ["time", "name", "Ax", "Ay", "Az", "Gx", "Gy", "Gz", "seq_num"]
            bluno_1_df = pd.DataFrame(bluno_1_collation_arr)
            bluno_1_df.to_csv(path_or_buf="../031024_output/bluno_1.csv", index=False, header=csv_header_arr)
            bluno_2_df = pd.DataFrame(bluno_2_collation_arr)
            bluno_2_df.to_csv(path_or_buf="../031024_output/bluno_2.csv", index=False, header=csv_header_arr)
            bluno_3_df = pd.DataFrame(bluno_3_collation_arr)
            bluno_3_df.to_csv(path_or_buf="../031024_output/bluno_3.csv", index=False, header=csv_header_arr)

            # after collation is complete
            # reset all arrays
            bluno_1_collation_arr = []
            bluno_2_collation_arr = []
            bluno_3_collation_arr = []
            bluno_1_prev_compare_arr = []
            bluno_2_prev_compare_arr = []
            bluno_3_prev_compare_arr = []
            bluno_1_curr_compare_arr = []
            bluno_2_curr_compare_arr = []
            bluno_3_curr_compare_arr = []
            # reset flags
            isCollate = False
            isB1Complete = False
            isB2Complete = False
            isB3Complete = False
            print("collation complete")
            isFullCycleComplete = True # set flag after one full iteration is complete and the data has been output -> prevent overwriting

def isAboveThreshold(prev_arr, curr_arr):
    FIXED_THRESHOLD = 10000
    AX_INDEX = 2
    AY_INDEX = 3
    AZ_INDEX = 4
    GX_INDEX = 5
    GY_INDEX = 6
    GZ_INDEX = 7

    total_prev_Ax = 0
    total_prev_Ay = 0
    total_prev_Az = 0
    total_prev_Gx = 0
    total_prev_Gy = 0
    total_prev_Gz = 0

    # populate mean_prev_X
    for data in prev_arr:
        # print(f"mean_prev_x calculation: {data}")
        total_prev_Ax += data[AX_INDEX]
        total_prev_Ay += data[AY_INDEX]
        total_prev_Az += data[AZ_INDEX]
        total_prev_Gx += data[GX_INDEX]
        total_prev_Gy += data[GY_INDEX]
        total_prev_Gz += data[GZ_INDEX]
    
    mean_prev_Ax = total_prev_Ax / 5
    mean_prev_Ay = total_prev_Ay / 5
    mean_prev_Az = total_prev_Az / 5
    mean_prev_Gx = total_prev_Gx / 5
    mean_prev_Gy = total_prev_Gy / 5
    mean_prev_Gz = total_prev_Gz / 5

    total_curr_Ax = 0
    total_curr_Ay = 0
    total_curr_Az = 0
    total_curr_Gx = 0
    total_curr_Gy = 0
    total_curr_Gz = 0

    # populate mean_curr_X
    for data in curr_arr:
        # print(f"curr mean data: {data}")
        total_curr_Ax += data[AX_INDEX]
        total_curr_Ay += data[AY_INDEX]
        total_curr_Az += data[AZ_INDEX]
        total_curr_Gx += data[GX_INDEX]
        total_curr_Gy += data[GY_INDEX]
        total_curr_Gz += data[GZ_INDEX]
    
    mean_curr_Ax = total_curr_Ax / 5
    mean_curr_Ay = total_curr_Ay / 5
    mean_curr_Az = total_curr_Az / 5
    mean_curr_Gx = total_curr_Gx / 5
    mean_curr_Gy = total_curr_Gy / 5
    mean_curr_Gz = total_curr_Gz / 5
    
    # compare threshold
    diff_Ax = abs(mean_curr_Ax-mean_prev_Ax)
    diff_Ay = abs(mean_curr_Ay-mean_prev_Ay)
    diff_Az = abs(mean_curr_Az-mean_prev_Az)
    diff_Gx = abs(mean_curr_Gx-mean_prev_Gx)
    diff_Gy = abs(mean_curr_Gy-mean_prev_Gy)
    diff_Gz = abs(mean_curr_Gz-mean_prev_Gz)

    # print(diff_Ax) # to remove

    max_diff = max(diff_Ax, diff_Ay, diff_Az ,diff_Gx, diff_Gy, diff_Gz)

    return max_diff > FIXED_THRESHOLD