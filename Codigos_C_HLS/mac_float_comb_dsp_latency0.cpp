void mac_float_comb_dsp_latency0(
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

#pragma HLS LATENCY min=0 max=0

    float mult;
    float acc;

#pragma HLS BIND_OP variable=mult op=fmul impl=maxdsp latency=0
#pragma HLS BIND_OP variable=acc  op=fadd impl=fulldsp latency=0

    mult = a * b;
    acc  = mult + c;

    *result = acc;
}