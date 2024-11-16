# HW/SW AI

Houses the code used for entire AI process from HW to SW, across 13 weeks of CG4002 capstone project. Project aims to predict certain moves based on list of actions, where the user will execute the moves in real time. IMUs are strapped on the player's right hand and leg, and data is sent to the Ultra96 FPGA through internal and external communications(not covered in this repo). When the data is received by the python script with PYNQ overlay, an output is predicted by the IP block generated from vivado (in the form of bitstream) and returned to the external comms, for further dissemination to the visualiser and back to internal communications. A temperature scaling confidence level scheme was attempted to filter out noise and unsure predictions based on the data sent from the player. Everything runs on the Programming Logic (PL) on the Ultra96, and communication is done using AXI DMA.

## List of moves
### Values corresponding to each action 
- Bowling = 1 
- Logout = 2 
- Rainbomb = 3 
- Reload = 4 
- Shield = 5 
- Soccer = 6 
- Volleyball = 7 
- Walk = 8 
- Continuous Walk = 9

Additionally, all predictions made that fall below the confidence threshold of 0.94 are reclassified to [9], as it is not an action of interest to other stakeholders in this system.

## Initial training of MLP model
The model is trained on a simple MLP model that is used to predict the moves based on waveforms collected. Initially, it was trained by collecting various features such as min, max, std etc but was found to be less consistent between players (due to different degrees and magnitudes of movement). The raw data is subsequently used to analyse the trends of each move when plotted against time, therefore giving a more generic prediction that suits players of various heights and arm length. `mlp_python` and `old_mlp_python` houses the abovementioned changes to the MLP model. Normalisation, adding noise and data augmentation methods are done to the training data to increase the number of datasets to train on, while varying the possible types of data that could come in from the IMU.

## Collection of data
With the help of internal comms, training data is collected from our IMUs and this will be used to train our MLP model. Data can be found in `collected_data`. Prior to our hardware being ready for data collection, an online dataset is used to help us train and set up the entire pipeline needed for our HW and SW AI. This can be found in `onlineset`, which was taken from the following author on [Kaggle](https://www.kaggle.com/datasets/harrisonlou/imu-glove/data).

## Converting of MLP model to C++
To create a bitstream in Vivado, we can utilise the High-level synthesis function that is provided by Vitis to convert C++ into an IP block. This can help us avoid using Verilog to rewrite the MLP model that we want. The MLP model is then rewritten into C++ with the weights trained from the Python side of the model, which allows us to recreate the exact same model that we want on our bitstream. Utilising `hls::stream` helps us recieve and send data from our Python script that we will be creating on the Ultra96. This can be found in `hls_cplusplus`.

## Overlaying the bitstream and using PYNQ
When the bitstream is complete, it is transfer (along with the hwh file) to the FPGA and the overlay is done using PYNQ. The data can then be sent and recieved, with the bitstream acting as the AI which serves as our prediction black box. The code can be found in `old_fpga_python` and `fpga_python`, with the main difference being how the AI component communicates with the external comms. 

