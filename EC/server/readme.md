## Eval Server

1. run the eval server with command "python3 WebSocketServer.py"
   a) Eval server hosts a Wesocket server listening on port 8001. The web interface is connected to this server

2. Launch the web page "html/index.html"
   a) Enter the ip address of the machine where you are running the eval server
   i) Typically you would launch the webpage from the laptop on which you are running the eval server
   IN sucha a case you can use the ip address 127.0.0.1
   b) Enter the password your eval client expects ( This is your 16 char AES key)

NOTE:

1. Eval server also hosts a TCP server which waits for a connection from the "eval client" on Ultra96
2. To understand the code start from WebSocketServer.handler()

## Eval Client

### Setup

1. Create a virtual env with `python3 -m venv env`
2. `source env/bin/activate`
3. Install dependencies: `pip3 install -r requirements.txt`

### Usage

1. If the `ENABLE_AI` flag is true, the AI server must be running first.
2. If the `ENABLE_FREE_PLAY` flag is false, the eval server must be running first. This probably involves opening index.html from the html folder as well.
3. Run eval_client `python3 eval_client.py`

### Key Files

1. eval_client.py: main eval client code
2. mqtt.py: mqtt client code
3. ../html/sim.html: simulator webpage

## Relay Node

Assuming you have cded into this directory (`server`)

1. `source ../env/bin/activate`
2. `python3 relay.py`
