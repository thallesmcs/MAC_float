// mac_float.cpp

// extern "C" {

void mac_float(
    float a,
    float b,
    float *result
)

{
#pragma HLS INTERFACE ap_none port=a
#pragma HLS INTERFACE ap_none port=b
#pragma HLS INTERFACE ap_none port=result
#pragma HLS INTERFACE ap_ctrl_none port=return

static float acc = 0.0f;

float mult = a * b;
acc = acc + mult;

*result = acc;
}

// }