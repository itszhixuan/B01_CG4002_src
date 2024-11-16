#!/bin/bash

TARGET=$1
ssh -R 8888:localhost:$1 capstone
