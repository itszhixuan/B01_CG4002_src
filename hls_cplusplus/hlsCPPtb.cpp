#include <iostream>
#include "hls_stream.h"
#include "ap_axi_sdata.h"

//struct AXIS_wLAST{
//    float data;
//    bool last;
//};

typedef ap_axis<32, 2, 5, 6> AXIS_wLAST;

// Instantiate MLP and test forward pass
void forward(hls::stream<AXIS_wLAST> &input_stream, hls::stream<AXIS_wLAST> &output_stream);

int main() {

	// Create input and output streams
	hls::stream<AXIS_wLAST> input_stream;
	hls::stream<AXIS_wLAST> output_stream;

	union fp_int {
		int ival;
		float fval;
	};

    float test_data[] = {
    		837.6, -2256.0, -720.0, -761.2, -1730.2, 10445.0, 4560.8, -10020.8, 1188.8, 21977.6, 203.0, 11890.8, 3754.4, -22634.4, -8132.0, 32767.0, 4614.4, 7901.6, 1560.8, -31456.8, -11483.2, 28013.6, 2564.6, 6357.4, 1744.8, -32768.0, -11436.8, 9792.2, 10237.6, 1196.4, 2639.2, -32768.0, -9608.0, -15324.2, 2232.0, -9112.2, 4686.4, -30260.8, -11560.0, -28690.0, -10332.8, -14284.8, 6884.8, -21540.0, -16370.4, -32768.0, -8936.2, -14337.0, 5329.6, -10174.4, -17486.4, -32768.0, -12156.2, -14258.8, 2001.6, -3029.6, -15740.0, -32768.0, -21189.4, -12458.4, -952.0, 2045.6, -18904.0, -32768.0, -24073.0, -7345.4, -935.2, 6221.6, -14956.8, -32768.0, -16974.6, -5287.0, -1524.0, 9124.0, -5270.4, -31535.2, -10363.6, -4281.2, -2240.0, 8956.0, 3224.8, -24478.0, -3421.2, -311.8, -2529.6, 8158.4, 10656.0, -12304.6, 5000.8, 4207.0, -3935.2, 9444.0, 16929.6, 2763.8, 7243.4, 8427.0, -4199.2, 10277.6, 16340.0, 19544.0, 8091.4, 12621.4, -2760.0, -36.0, 7345.6, 31518.6, 4048.2, 17248.6, -388.0, -8006.4, -5965.6, 20963.2, -7690.2, 12390.8, -4605.6, -4311.2, -14380.8, 6648.2, -10816.6, 2270.2, -7759.2, 4438.4, -11350.4, -10296.2, 1440.6, -8807.0, -5923.2, -1180.8, -11648.0, -12244.2, 11782.6, -15924.8, -3463.2, 72.0, -10152.8, -19107.4, 1249.6, -17109.8, -4896.0, 1939.2, -5936.8, -17742.6, -3193.6, -13598.0, -5943.2, 9778.4, 477.6, -6924.8, 6766.0, -6335.6, -5122.4, 14881.6, -1538.4, 8789.6, 16134.6, 2833.0, -3176.8, 15240.0, -7898.4, 25036.4, 19352.2, 13349.0, 692.0, 10168.8, -14800.0, 32301.8, 21296.0, 20892.0, 3288.0, 1416.8, -20844.8, 32767.0, 27619.2, 25851.4, 10241.6, -6080.8, -21548.0, 28029.8, 30184.6, 27491.2, 18654.4, -8847.2, -16732.8, 18502.0, 23440.4, 25873.8, 19909.6, -9854.4, -11851.2, 12517.4, 2283.8, 19665.2, 16521.6, -14341.6, -13492.8, 10462.2, -7576.8, 11174.6, 15476.8, -17624.0, -11661.6, 2240.8, 7476.0, 2724.4, 16287.2, -16612.0, -8518.4, -6492.2, 4598.0, -4021.4, 14513.6, -13459.2, -8218.4, -9335.2, -6787.2, -8035.0, 12650.4, -10805.6, -10200.0, -10791.6, -7023.8, -11089.6, 12510.4, -8801.6, -10103.2, -10226.4, -1807.6, -12235.2, 6987.2, 11514.4, 9105.6, 98.0, -992.4, 385.8, 6994.4, 11910.4, 8636.0, 698.6, -967.0, -80.2, 7174.4, 12269.6, 8222.4, 852.0, -405.6, 204.8, 7420.8, 12064.0, 8488.0, 647.4, 150.2, 398.2, 7614.4, 11476.0, 8997.6, 454.8, 227.0, -93.4, 7512.0, 11327.2, 9419.2, 516.8, -311.8, -1045.6, 7108.0, 11833.6, 9114.4, 742.2, -901.2, -1658.2, 6899.2, 12781.6, 8265.6, 678.0, -840.2, -1184.8, 6772.0, 13269.6, 7768.0, 205.6, -98.0, 88.4, 7004.0, 12727.2, 8165.6, -511.2, 639.4, 1082.6, 7423.2, 11892.8, 8894.4, -626.6, 965.8, 1448.0, 7626.4, 11259.2, 9417.6, -375.6, 784.8, 891.6, 7452.0, 10887.2, 9552.8, 280.4, 295.0, -77.2, 7109.6, 11149.6, 9481.6, 990.0, -256.0, -1165.8, 6847.2, 11878.4, 9109.6, 1116.6, -761.8, -1602.2, 6418.4, 12679.2, 8354.4, 550.6, -819.4, -1187.6, 6308.0, 12947.2, 7778.4, -135.6, -292.2, -405.6, 7047.2, 12886.4, 8053.6, -224.6, 740.2, 642.8, 7413.6, 12369.6, 8968.0, -364.0, 1509.8, 1331.4, 7078.4, 11735.2, 9676.0, -635.8, 1352.4, 1427.4, 6492.8, 11357.6, 9860.8, -619.6, 354.8, 813.4, 6876.8, 11032.8, 9772.8, -125.4, -484.0, 117.4, 7372.8, 11203.2, 9572.8, 490.2, -701.4, -400.0, 6999.2, 11583.2, 9249.6, 737.4, -661.2, -586.2, 6815.2, 11968.0, 8988.8, 708.4, -597.0, -584.6, 6852.8, 11904.0, 8920.0, 579.4, -379.2, -553.4, 7046.4, 12092.0, 9070.4, 496.2, -113.2, -249.8, 6908.8, 11854.4, 9256.8, 314.2, -220.2, -139.6, 6935.2, 11660.8, 9325.6, 360.6, -461.8, -190.2, 6941.6, 11588.0, 9297.6, 592.8, -676.4, -559.8, 6944.8, 11773.6, 9191.2, 721.0, -886.4, -921.4, 6870.4, 12160.8, 8864.8, 772.6, -928.6, -953.6, 6822.4, 12551.2, 8443.2, 663.6, -609.8, -568.2, 6812.0, 12512.0, 8440.0, 374.0, -173.2, -90.8, 6932.8, 12184.0, 8789.6, 205.4, 98.2, 184.8, 6894.4, 11900.0, 9045.6, 198.8, -24.4, 75.8, 6860.0, 11952.8, 8969.6, 301.6, -304.4, -169.6, 6884.8, 12174.4, 8705.6, 387.8, -423.6, -302.8
    };

    fp_int convert;

    for (int i = 0; i < 456; ++i) {
    	AXIS_wLAST input_value;
    	std::cout << "Input " << ": " << test_data[i] << std::endl;
    	convert.fval = test_data[i];
    	input_value.data = convert.ival;
    	std::cout << "Converted preInput " << ": " << input_value.data << std::endl;
    	if (i != 455) {
    		input_value.last = 0;
    	} else {
    		input_value.last = 1;
    	}
        input_stream.write(input_value); // Example data
        std::cout << "Input " << ": " << input_value.data << std::endl;
    }

    forward(input_stream, output_stream);
    // Additional code to see if confidence can be implemented
    AXIS_wLAST output_val;
    output_val = output_stream.read();
    std::cout << "Output Value 1: " << output_val.data << std::endl;

    AXIS_wLAST output_val2;
	output_val2 = output_stream.read();
	std::cout << "Output Value 2: " << output_val2.data << std::endl;

    AXIS_wLAST output_val3;
	output_val3 = output_stream.read();
	std::cout << "Output Value 3: " << output_val3.data << std::endl;

	AXIS_wLAST output_val4;
	output_val4 = output_stream.read();
	std::cout << "Output Value 4: " << output_val4.data << std::endl;

	AXIS_wLAST output_val5;
	output_val5 = output_stream.read();
	std::cout << "Output Value 5: " << output_val5.data << std::endl;

	AXIS_wLAST output_val6;
	output_val6 = output_stream.read();
	std::cout << "Output Value 6: " << output_val6.data << std::endl;

	AXIS_wLAST output_val7;
	output_val7 = output_stream.read();
	std::cout << "Output Value 7: " << output_val7.data << std::endl;

	AXIS_wLAST output_val8;
	output_val8 = output_stream.read();
	std::cout << "Output Value 8: " << output_val8.data << std::endl;

	AXIS_wLAST output_val9;
	output_val9 = output_stream.read();
	std::cout << "Output Value 9: " << output_val9.data << std::endl;

	AXIS_wLAST output_val10;
	output_val10 = output_stream.read();
	std::cout << "Output Value 10: " << output_val10.data << std::endl;

	AXIS_wLAST output_val11;
	output_val11 = output_stream.read();
	std::cout << "Output Value 11: " << output_val11.data << std::endl;

	AXIS_wLAST output_val13;
	output_val13 = output_stream.read();
	std::cout << "Output Value 12: " << output_val13.data << std::endl;

	AXIS_wLAST output_val12;
	output_val12 = output_stream.read();
	std::cout << "Output Value 13: " << output_val12.data << std::endl;
	return 0;
}
