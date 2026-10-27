    void mac_float_comb(
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
    
#pragma HLS LATENCY min=0 max=0
    
    float mult = a * b;
    float acc  = mult + c;

    *result = acc;
}
