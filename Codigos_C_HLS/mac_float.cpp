// mac_float.cpp

// extern "C" {

void mac_float(
    float a,
    float b,
    float c,
    float *result
)

{
#pragma HLS INTERFACE ap_none port=a
#pragma HLS INTERFACE ap_none port=b
#pragma HLS INTERFACE ap_none port=c
#pragma HLS INTERFACE ap_none port=result
#pragma HLS INTERFACE ap_ctrl_none port=return

    float mult = a * b;
    float acc  = mult + c;

    *result = acc;
}

// }