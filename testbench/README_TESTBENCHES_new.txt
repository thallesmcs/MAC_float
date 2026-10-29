Testbenches padronizados para thallesmcs/MAC_float

Vetores comuns:
0:  2 *  3 => produto   6 => ACC   6
1: -1 *  4 => produto  -4 => ACC   2
2:  5 *  2 => produto  10 => ACC  12
3: -3 * -2 => produto   6 => ACC  18
4:  7 *  1 => produto   7 => ACC  25
5:  4 * -2 => produto  -8 => ACC  17
6: -2 *  5 => produto -10 => ACC   7
7:  6 *  2 => produto  12 => ACC  19

Intervalos usados a partir do RTL atual:
mac_float                       : 11 ciclos
mac_float_simp                  : 11 ciclos
mac_float_comb                  : 10 ciclos
mac_float_comb_dsp              : 11 ciclos
mac_float_comb_dsp_latency0     : 1 ciclo (saida combinacional next_acc)
mac_float_pipeline              : 5 ciclos (HLS_SYN_TPT=5)
mac_int                         : 3 ciclos

Cada TB grava:
<arquitetura>/testbench/<arquitetura>_output.csv

IMPORTANTE:
Os caminhos de CSV pressupõem que o simulador seja iniciado na raiz do repositorio.
Os diretorios <arquitetura>/testbench/ precisam existir antes da simulacao.
O ACC estatico do RTL atual inicia em zero, mas ap_rst nao necessariamente zera esse registrador;
por isso cada TB executa uma unica sequencia acumulativa por simulacao e mantem a=b=0 durante reset.
