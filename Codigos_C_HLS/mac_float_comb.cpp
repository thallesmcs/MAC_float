void mac_float_comb(
    float a,
    float b,
    float *result
) {
#pragma HLS INTERFACE ap_none port=a
#pragma HLS INTERFACE ap_none port=b
#pragma HLS INTERFACE ap_none port=result
#pragma HLS INTERFACE ap_ctrl_none port=return

#pragma HLS LATENCY min=0 max=0

    static float acc = 0.0f;

    float mult = a * b;
    acc = acc + mult;

    *result = acc;
}