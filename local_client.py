import socket

def start_client():
    host = "172.26.191.207"
    port = 65432

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        print("Client: Connected to server")

        data = "[[[12776, -3608, -12876, -261, -57, 669], [13984, -3804, -13560, 674, 1648, 3750], [14760, -7360, -12084, 5030, 3020, 7450], [15852, -11704, -14932, 16898, 7492, 7037], [16168, -16872, -12448, 32767, 9018, -1356], [15988, -14060, -8940, 32276, 11522, 11007], [15296, -22076, -3060, 32767, 12217, 4643], [12952, -13848, -3912, 32767, 10457, -3843], [10868, -8376, -2476, 32767, 11928, -1686], [11252, -9444, -852, 32767, 14644, 1381], [9740, -9836, 956, 32767, 17660, -2265], [8644, -5420, 3864, 29678, 16701, -3415], [8152, -4712, 1896, 25984, 18304, -2115], [8008, -2232, 4556, 22812, 20204, -31], [5988, 308, 7628, 15946, 17073, 4352], [5248, -1796, 6204, 11774, 12034, 5458], [3648, 1064, 4856, 8820, 8204, 2311], [2156, 1288, 3628, 6111, 3651, 2361], [1080, 1316, 3304, 1283, -2873, -865], [1192, 1492, 3836, -2843, -11888, -2653], [1688, 1120, 4424, -3342, -21003, -1534], [4764, -5632, 5032, -9303, -32768, -4588], [-20, 212, -1620, -12003, -32768, -7533], [15952, 2564, 1496, -11323, -32768, 1996], [15976, 1192, 3428, -8149, -32768, 8475], [30864, -6840, -6696, -4917, -32768, 6289], [32767, -8124, -16440, -14265, -32768, 1649], [32767, -12220, -8268, -23779, -32768, 1795], [31884, -22504, -6108, -17332, -16153, -5405], [23520, -14004, -1800, -7455, -2089, -14190], [22684, 5992, -11288, 726, 1734, 2449], [31236, -2120, -7180, 7270, 21284, 25397], [32767, -7520, -13012, 8359, 32767, 22145], [32767, -8356, -13552, 20809, 32767, 14692], [25044, -9536, -10080, 24470, 32767, 10625], [20912, -4544, -636, 16197, 32767, 23315], [14656, -14860, 7016, 17611, 32767, 22674], [7968, -8700, 14184, 18269, 32767, 7620], [2036, -2932, 12568, 18438, 32767, 11140], [-2824, -4512, 9056, 12847, 32767, 9773], [-2764, -6356, 17292, 15105, 32767, 12376], [-788, -7364, 15988, 27353, 32767, 7046], [-1096, -4524, 15160, 30709, 32767, 5444], [-3052, -4740, 16292, 28451, 32767, 10364], [-5424, -3364, 16164, 29578, 32767, 3550], [-6132, 396, 14384, 24535, 31101, 1559], [-8456, 516, 12344, 21123, 29691, 4151], [-10192, 2492, 9924, 23128, 27667, 5940], [-11124, 252, 6328, 25461, 22804, -92], [-11336, 984, 3640, 19278, 20055, -4445], [-10500, 2116, 2060, 12243, 17888, -2564], [-10128, -744, 1276, 10007, 14182, -3088], [-13900, 1780, -1536, 10421, 12209, -11486], [-15392, 7012, -2896, 6442, 7273, -8148], [-16612, 2168, -2944, 3310, -732, -8819], [-20284, 2088, -336, -4225, -15807, -19257], [-26660, 6132, -12728, -10403, -29524, -18849], [-16476, 3796, 276, -8746, -32768, -17744], [-17612, 2528, 4108, -11842, -32768, -17784], [-16128, 2448, -424, -4243, -32768, -25042], [-8616, 1176, 5376, 3844, -32768, -26534], [11064, 22536, -26316, -1369, -32768, -8536], [1380, 1204, -32768, 10607, -32768, 12744], [28604, -6532, 9184, -6567, -32768, -6258], [9680, -3596, 21392, -19950, -29823, -8505], [12896, -3516, 2000, -14878, -9916, -345], [10644, -5100, 3108, 5162, 13708, 4392], [11520, -2848, 6252, 25697, 19860, 3496], [12432, -1952, 92, 27273, 17709, -2839], [10448, 6964, -13136, 18865, 22000, -133], [3020, 8716, -16108, 9072, 32767, 10538], [-2948, 7608, -11496, 4574, 32767, 19475], [-2512, 8112, 5472, 10957, 32727, 21361], [480, -312, 13392, -3439, 17945, 18517], [-1100, 3760, 2592, -7366, 12638, 16616], [-248, -1852, 11660, -8670, 9013, 10696], [-2416, -2340, 4852, -17791, 9159, 105], [-4456, -3388, 15036, -23839, 7510, -1239], [-3036, -16572, 22536, -27861, -26517, -10584], [1320, -8680, 19160, -26759, -32768, -21646]], [[16392, 268, 1996, 1355, 4790, 5898], [16280, 640, 2036, 1181, 5632, 5899], [16284, 720, 2016, 1380, 5330, 5775], [16444, 924, 2056, 1676, 4896, 5777], [16468, 876, 2036, 1814, 4880, 5682], [16360, 880, 2036, 1439, 5533, 5752], [16312, 932, 1980, 1238, 6238, 5635], [16240, 896, 1968, 1656, 6324, 5823], [16136, 884, 1880, 1562, 6204, 5741], [16220, 844, 1852, 1596, 5837, 5640], [16200, 1164, 2000, 1598, 5621, 5783], [16204, 868, 1968, 1244, 5632, 5706], [16292, 916, 1976, 1265, 5633, 5695], [16232, 924, 1936, 1326, 5853, 5810], [16352, 924, 1980, 1665, 5752, 5699], [16476, 960, 2008, 1870, 5757, 5695], [16320, 964, 1968, 1405, 5857, 5716], [16384, 928, 1956, 1301, 5634, 5729], [16288, 872, 1936, 1457, 5520, 5615], [16340, 968, 1948, 1574, 5329, 5665], [16372, 972, 1980, 1454, 5590, 5668], [16412, 840, 1944, 1611, 5620, 5638], [16304, 928, 1936, 1390, 5700, 5588], [16376, 1004, 1976, 1328, 5638, 5667], [16292, 896, 1916, 1339, 5460, 5520], [16256, 840, 1984, 1492, 5401, 5501], [16304, 1004, 1976, 1328, 5638, 5667], [16292, 896, 1916, 1339, 5460, 5520], [16256, 840, 1984, 1492, 5401, 5501], [16392, 268, 1996, 1355, 4790, 5898], [16280, 640, 2036, 1181, 5632, 5899], [16284, 720, 2016, 1380, 5330, 5775], [16444, 924, 2056, 1676, 4896, 5777], [16468, 876, 2036, 1814, 4880, 5682], [16360, 880, 2036, 1439, 5533, 5752], [16312, 932, 1980, 1238, 6238, 5635], [16240, 896, 1968, 1656, 6324, 5823], [16136, 884, 1880, 1562, 6204, 5741], [16220, 844, 1852, 1596, 5837, 5640], [16200, 1164, 2000, 1598, 5621, 5783], [16204, 868, 1968, 1244, 5632, 5706], [16292, 916, 1976, 1265, 5633, 5695], [16232, 924, 1936, 1326, 5853, 5810], [16352, 924, 1980, 1665, 5752, 5699], [16476, 960, 2008, 1870, 5757, 5695], [16320, 964, 1968, 1405, 5857, 5716], [16384, 928, 1956, 1301, 5634, 5729], [16288, 872, 1936, 1457, 5520, 5615], [16340, 968, 1948, 1574, 5329, 5665], [16372, 972, 1980, 1454, 5590, 5668], [16412, 840, 1944, 1611, 5620, 5638], [16304, 928, 1936, 1390, 5700, 5588], [16376, 1004, 1976, 1328, 5638, 5667], [16292, 896, 1916, 1339, 5460, 5520], [16256, 840, 1984, 1492, 5401, 5501]]]"
        data = data.encode('utf-8')
        for i in range(0, len(data), 2048):
            print(f"Client sending data: {data[i:i + 2048]}")
            s.sendall(data[i:i + 2048])

        response = s.recv(2048).decode()  # Receive response from the server
        print(f"Client: Received {response}")
            

        # Send 'END' to signal termination
        s.sendall(b"END")
        print("Client: Sent END signal")


if __name__ == "__main__":
    start_client()
