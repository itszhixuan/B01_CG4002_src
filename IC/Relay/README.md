# INTERNAL COMMS - RELAY NODE
This folder contains the code required to run the relay node for Internal Comms. The relay node enables your machine to connect to and exchange data with the Bluno Beetles. It assumes that the MAC addresses of the Bluno Beetles are stored in the _config.json_ file and that the Bluno Beetles are running the code found in _IC/Bluno_.

## SETUP
### TOOLS
This code requires the _bluepy_ library to function. As a result, it can only be run on Linux-based systems (e.g. Fedora, Linux Mint).

### SETTING UP VIRTUAL ENVIRONMENT
1. Create a virtual environment: `python3 -m venv relayenv`
2. Activate the virtual environment: `source relayenv/bin/activate`
3. Install the required libraries: `pip install -r requirements.txt`

## INSTRUCTIONS TO RUN SCRIPT
1. Update the MQTT broker details in _mqtt.py_.
2. Enter the MAC addresses of the Beetles being used in _config.json_.
3. Specify the player number (1 or 2) for the computer in *relay_node.py* at **line 48**.
4. Run the script: `python relay_node.py`