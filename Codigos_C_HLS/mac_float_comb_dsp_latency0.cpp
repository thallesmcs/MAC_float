void mac_float_comb_dsp_latency0(
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

    float mult;
    float next_acc;

#pragma HLS BIND_OP variable=mult op=fmul impl=maxdsp latency=0
#pragma HLS BIND_OP variable=next_acc op=fadd impl=fulldsp latency=0

    mult = a * b;
    next_acc = acc + mult;

    acc = next_acc;

    *result = acc;
}