void mac_float_comb_dsp(
    float a,
    float b,
    float c,
    float *result
) {
#pragma HLS INTERFACE ap_none port=a
#pragma HLS INTERFACE ap_none port=b
#pragma HLS INTERFACE ap_none port=c
#pragma HLS INTERFACE ap_none port=result
#pragma HLS INTERFACE ap_ctrl_none port=return

    float mult;
    float acc;

#pragma HLS BIND_OP variable=mult op=fmul impl=maxdsp
#pragma HLS BIND_OP variable=acc op=fadd impl=fulldsp

    mult = a * b;
    acc  = mult + c;

    *result = acc;
}