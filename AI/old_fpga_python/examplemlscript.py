from pynq import Overlay, allocate
import pynq.lib.dma
import sys, os
import numpy as np
import struct
import sys
import json

def MLmodel(raw_data):
    ##input_data = sys.stdin.read().strip()
    print(raw_data)
    input_data = json.loads(raw_data)

    curr_dir = sys.path[0]
    overlay = Overlay(os.path.join(curr_dir, 'testhighclock.bit'))

    dma = overlay.dma
    dma_send = dma.sendchannel
    dma_recv = dma.recvchannel


    # Allocate input and output buffers
    input_buffer = allocate(shape=(144,), dtype=np.int32)
    output_buffer = allocate(shape=(1,), dtype=np.int32)

    test_data = [1.0187,1.1,0.96,0.02604018,0.0006780909,1.0190295,0.29246312,0.15625152,3.019,3.07,2.96,0.021625835,0.00046767676,3.0190766,-0.1620381,0.24577479,9.06,9.14,8.98,0.033333335,0.0011111111,9.0600605,-0.0050092763,-0.37390548,0.0964,0.12,0.08,0.0071802195,5.1555555e-05,0.09666437,0.49530438,0.30859077,0.0308,0.05,0.02,0.00691653,4.7838384e-05,0.031559467,0.4542584,0.541849,0.0053,0.01,0.0,0.0050161355,2.5161617e-05,0.00728011,-0.12205509,-2.0260355,-8.3721,-8.24,-8.47,0.04063374,0.001651101,8.372197,0.04174422,0.28397015,4.5221,4.61,4.44,0.032823216,0.0010773636,4.5222178,-0.07632977,-0.16051912,2.6643,2.79,2.57,0.03649422,0.0013318283,2.6645474,0.38471994,0.8125317,0.0682,0.08,0.06,0.004114522,1.6929293e-05,0.06832276,-1.2379956,0.8811203,-0.135,-0.13,-0.14,0.005025189,2.5252526e-05,0.13509256,0.0,-2.041237,0.0128,0.03,0.0,0.0060436125,3.6525253e-05,0.014142135,0.34694535,0.2899276,-7.6992,-7.64,-7.76,0.023556508,0.0005549091,7.6992354,-0.2065083,0.119233504,5.4367,5.5,5.36,0.026402287,0.0006970808,5.4367633,-0.010191155,0.41262498,0.9005,1.0,0.82,0.03627546,0.0013159091,0.90122306,0.035319686,0.08802274,0.1481,0.16,0.14,0.005259911,2.7666667e-05,0.14819244,-0.19136243,0.115383916,0.1055,0.13,0.08,0.008918826,7.9545454e-05,0.105872564,0.15145783,0.46847537,0.012,0.08,-0.01,0.012060454,0.00014545454,0.016970562,1.8261179,9.307672]

    def float_to_int(f):
        packed = struct.pack('f', f) 
        i = struct.unpack('I', packed)[0]
        return i

    ## changing to input_data
    
    int_data = [float_to_int(f) for f in input_data]
    input_buffer[:] = int_data

    output_buffer.fill(0)
    dma_send.transfer(input_buffer)
    dma_recv.transfer(output_buffer)
    dma_send.wait()
    dma_recv.wait()
    
    return output_buffer

    print("Input Buffer (Sent Data):", input_buffer)
    print("Output Buffer (Received Data):", output_buffer)