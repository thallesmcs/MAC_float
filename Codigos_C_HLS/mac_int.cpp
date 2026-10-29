void mac_int(
    int a,
    int b,
    int *result
) {
#pragma HLS INTERFACE ap_none port=a
#pragma HLS INTERFACE ap_none port=b
#pragma HLS INTERFACE ap_none port=result
#pragma HLS INTERFACE ap_ctrl_none port=return

    static int acc = 0;

    int mult = a * b;
    acc = acc + mult;

    *result = acc;
}