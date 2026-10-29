void mac_float_simp(
    float a,
    float b,
    float *result
) {
#pragma HLS INTERFACE ap_none port=a
#pragma HLS INTERFACE ap_none port=b
#pragma HLS INTERFACE ap_none port=result
#pragma HLS INTERFACE ap_ctrl_none port=return

    static float acc = 0.0f;

    acc += a * b;

    *result = acc;
}