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
        -6.624742,0.736009,5.314845,6.66,0.359828,0.310027,-0.433093,1.072423,17.245576,-0.153402
    };

    fp_int convert;

    for (int i = 0; i < 10; ++i) {
    	AXIS_wLAST input_value;
    	std::cout << "Input " << ": " << test_data[i] << std::endl;
    	convert.fval = test_data[i];
    	input_value.data = convert.ival;
    	std::cout << "Converted preInput " << ": " << input_value.data << std::endl;
    	if (i != 9) {
    		input_value.last = 0;
    	} else {
    		input_value.last = 1;
    	}
        input_stream.write(input_value); // Example data
        std::cout << "Input " << ": " << input_value.data << std::endl;
    }

    forward(input_stream, output_stream);
    return 0;
}
