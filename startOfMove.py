## Currently, plan for 3 bluno data that detects motion
## Bluno 1: Right arm
## Bluno 2: Right leg
## Bluno 3: Left arm

## Plan is to compare 2 0.5s frames of data, and if any of the IMU data exceeds a certain threshold

## Data is sent in as an array of arrays
## Example Input (raw_data reflects the data from the first 0.5s frame)
## assuming 0.1s sends one set of data
import numpy as np
from scipy.stats import skew, kurtosis

threshold = 0.2

raw_data = [[0.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65],
            [0.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65],
            [0.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65],
            [0.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65],
            [0.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65]
            ]

## Example Input (raw_data reflects the data from the second 0.5s frame)
## assuming 0.1s sends one set of data
raw_data_2 = [[10.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65],
            [10.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65],
            [10.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65],
            [10.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65],
            [10.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65]
            ]

## assuming 0.1s sends one set of data (third window that comes after)
raw_data_3 = [[0.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65],
            [0.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65],
            [0.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65],
            [0.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65],
            [0.765, 0.734, 0.752, 6.23, 6.54, 6.76,0.323, 0.423, 0.311, 4.54, 4.32, 4.47,0.132, 0.323, 0.412, 4.12, 4.22, 4.65]
            ]

class halfSecondWindow:
    def __init__(self) -> None:
        # Bluno 1
        self.acc_x_1 = []
        self.acc_y_1 = []
        self.acc_z_1 = []
        self.gry_x_1 = []
        self.gry_y_1 = []
        self.gry_z_1 = []
        # Bluno 2
        self.acc_x_2 = []
        self.acc_y_2 = []
        self.acc_z_2 = []
        self.gry_x_2 = []
        self.gry_y_2 = []
        self.gry_z_2 = []
        # Bluno 3
        self.acc_x_3 = []
        self.acc_y_3 = []
        self.acc_z_3 = []
        self.gry_x_3 = []
        self.gry_y_3 = []
        self.gry_z_3 = []

    def read_values(self, raw_data):
        for i in raw_data:
            self.acc_x_1.append(abs(i[0]))
            self.acc_y_1.append(abs(i[1]))
            self.acc_z_1.append(abs(i[2]))
            self.gry_x_1.append(abs(i[3]))
            self.gry_y_1.append(abs(i[4]))
            self.gry_z_1.append(abs(i[5]))
            self.acc_x_2.append(abs(i[6]))
            self.acc_y_2.append(abs(i[7]))
            self.acc_z_2.append(abs(i[8]))
            self.gry_x_2.append(abs(i[9]))
            self.gry_y_2.append(abs(i[10]))
            self.gry_z_2.append(abs(i[11]))
            self.acc_x_3.append(abs(i[12]))
            self.acc_y_3.append(abs(i[13]))
            self.acc_z_3.append(abs(i[14]))
            self.gry_x_3.append(abs(i[15]))
            self.gry_y_3.append(abs(i[16]))
            self.gry_z_3.append(abs(i[17]))

    def merge_values(self, first,second):
        
        for i in range(len(first.acc_x_1)):
            self.acc_x_1.append(first.acc_x_1[i])
            self.acc_x_1.append(second.acc_x_1[i])
            self.acc_y_1.append(first.acc_y_1[i])
            self.acc_y_1.append(second.acc_y_1[i])
            self.acc_z_1.append(first.acc_z_1[i])
            self.acc_z_1.append(second.acc_z_1[i])

            self.gry_x_1.append(first.gry_x_1[i])
            self.gry_x_1.append(second.gry_x_1[i])
            self.gry_y_1.append(first.gry_y_1[i])
            self.gry_y_1.append(second.gry_y_1[i])
            self.gry_z_1.append(first.gry_z_1[i])
            self.gry_z_1.append(second.gry_z_1[i])

            self.acc_x_2.append(first.acc_x_2[i])
            self.acc_x_2.append(second.acc_x_2[i])
            self.acc_y_2.append(first.acc_y_2[i])
            self.acc_y_2.append(second.acc_y_2[i])
            self.acc_z_2.append(first.acc_z_2[i])
            self.acc_z_2.append(second.acc_z_2[i])

            self.gry_x_2.append(first.gry_x_2[i])
            self.gry_x_2.append(second.gry_x_2[i])
            self.gry_y_2.append(first.gry_y_2[i])
            self.gry_y_2.append(second.gry_y_2[i])
            self.gry_z_2.append(first.gry_z_2[i])
            self.gry_z_2.append(second.gry_z_2[i])

            self.acc_x_3.append(first.acc_x_3[i])
            self.acc_x_3.append(second.acc_x_3[i])
            self.acc_y_3.append(first.acc_y_3[i])
            self.acc_y_3.append(second.acc_y_3[i])
            self.acc_z_3.append(first.acc_z_3[i])
            self.acc_z_3.append(second.acc_z_3[i])

            self.gry_x_3.append(first.gry_x_3[i])
            self.gry_x_3.append(second.gry_x_3[i])
            self.gry_y_3.append(first.gry_y_3[i])
            self.gry_y_3.append(second.gry_y_3[i])
            self.gry_z_3.append(first.gry_z_3[i])
            self.gry_z_3.append(second.gry_z_3[i])

    def calculate_statistics(self):
        features = [
            'acc_x_1', 'acc_y_1', 'acc_z_1', 'gry_x_1', 'gry_y_1', 'gry_z_1',
            'acc_x_2', 'acc_y_2', 'acc_z_2', 'gry_x_2', 'gry_y_2', 'gry_z_2',
            'acc_x_3', 'acc_y_3', 'acc_z_3', 'gry_x_3', 'gry_y_3', 'gry_z_3'
        ]

        stats = []

        # Loop through each feature
        for feature in features:
            data = np.array(getattr(self, feature))  # Get the list of data using getattr
            ##print("Current Feature: " + feature)
            ##print(data)
            # Calculate statistics
            mean = np.mean(data)
            max_val = np.max(data)
            min_val = np.min(data)
            std = np.std(data)
            var = np.var(data)
            rms = np.sqrt(np.mean(np.square(data)))
            skewness = skew(data)
            kurt = kurtosis(data)
            
            # Store the results in a dictionary
            stats.extend([mean, max_val, min_val, std, var, rms, skewness, kurt])
            
            ##print([mean, max_val, min_val, std, var, rms, skewness, kurt])

        return stats

def isAboveThreshold(firstWindow,secondWindow):
    ## i could probably improve efficiency by checking with threshold everytime a mean is calculated
    ## Bluno 1
    mean_ax_1 = abs(np.asarray(firstWindow.acc_x_1).mean()-np.asarray(secondWindow.acc_x_1).mean())
    mean_ay_1 = abs(np.asarray(firstWindow.acc_y_1).mean()-np.asarray(secondWindow.acc_y_1).mean())
    mean_az_1 = abs(np.asarray(firstWindow.acc_z_1).mean()-np.asarray(secondWindow.acc_z_1).mean())
    mean_gx_1 = abs(np.asarray(firstWindow.gry_x_1).mean()-np.asarray(secondWindow.gry_x_1).mean())
    mean_gy_1 = abs(np.asarray(firstWindow.gry_y_1).mean()-np.asarray(secondWindow.gry_y_1).mean())
    mean_gz_1 = abs(np.asarray(firstWindow.gry_z_1).mean()-np.asarray(secondWindow.gry_z_1).mean())
    ## Bluno 2
    mean_ax_2 = abs(np.asarray(firstWindow.acc_x_2).mean()-np.asarray(secondWindow.acc_x_2).mean())
    mean_ay_2 = abs(np.asarray(firstWindow.acc_y_2).mean()-np.asarray(secondWindow.acc_y_2).mean())
    mean_az_2 = abs(np.asarray(firstWindow.acc_z_2).mean()-np.asarray(secondWindow.acc_z_2).mean())
    mean_gx_2 = abs(np.asarray(firstWindow.gry_x_2).mean()-np.asarray(secondWindow.gry_x_2).mean())
    mean_gy_2 = abs(np.asarray(firstWindow.gry_y_2).mean()-np.asarray(secondWindow.gry_y_2).mean())
    mean_gz_2 = abs(np.asarray(firstWindow.gry_z_2).mean()-np.asarray(secondWindow.gry_z_2).mean())
    ## Bluno 3
    mean_ax_3 = abs(np.asarray(firstWindow.acc_x_3).mean()-np.asarray(secondWindow.acc_x_3).mean())
    mean_ay_3 = abs(np.asarray(firstWindow.acc_y_3).mean()-np.asarray(secondWindow.acc_y_3).mean())
    mean_az_3 = abs(np.asarray(firstWindow.acc_z_3).mean()-np.asarray(secondWindow.acc_z_3).mean())
    mean_gx_3 = abs(np.asarray(firstWindow.gry_x_3).mean()-np.asarray(secondWindow.gry_x_3).mean())
    mean_gy_3 = abs(np.asarray(firstWindow.gry_y_3).mean()-np.asarray(secondWindow.gry_y_3).mean())
    mean_gz_3 = abs(np.asarray(firstWindow.gry_z_3).mean()-np.asarray(secondWindow.gry_z_3).mean())

    significantChange = max([mean_ax_1, mean_ay_1, mean_az_1, mean_gx_1, mean_gy_1, mean_gz_1, 
                              mean_ax_2, mean_ay_2, mean_az_2, mean_gx_2, mean_gy_2, mean_gz_2,
                              mean_ax_3, mean_ay_3, mean_az_3, mean_gx_3, mean_gy_3, mean_gz_3])
    
    if (significantChange > threshold):
        print(significantChange)
        return True
    return False

def isMove(firstWindow, secondWindow):
    detectedMove = isAboveThreshold(firstWindow, secondWindow)
    print(detectedMove)
    ## Assuming we only need the first second, and that would be 10 arrays
    if detectedMove==True:
        ## Get the 10 arrays
        thirdWindow = halfSecondWindow()
        thirdWindow.read_values(raw_data_3)
        ## merge data
        combinedWindow = halfSecondWindow()
        combinedWindow.merge_values(secondWindow, thirdWindow)
        ## Do feature extraction
        ##print(combinedWindow.acc_x_1)
        stats = combinedWindow.calculate_statistics()
        print(len(stats))
        ## Send to model
        ## Get result back

    
firstWindow = halfSecondWindow()
firstWindow.read_values(raw_data)
secondWindow = halfSecondWindow()
secondWindow.read_values(raw_data_2)
preparedData = []
preparedData.append(raw_data_2)
##print(preparedData)
##print(len(preparedData))
isMove(firstWindow, secondWindow)
##print(firstWindow.acc_x_2)