# Guia dos códigos C/C++, VHDL e Tcl

As pastas contêm versões de um MAC (*Multiply-Accumulate*) que calcula `result = a × b + c`, com entradas e saída de 32 bits. As versões `mac_float*` usam ponto flutuante de precisão simples; `mac_int` usa aritmética inteira. O valor `c` é uma entrada externa, sem acumulação automática entre operações.

Os arquivos `.cpp` da pasta `Codigos_C_HLS/` são os códigos-fonte C++ usados para gerar cada versão pelo Vitis HLS. Os arquivos `.vhd` descrevem o circuito e as conexões entre seus componentes. Nas versões de ponto flutuante, os arquivos auxiliares são adaptadores (*wrappers*) para IPs aritméticos da Xilinx; os scripts `_ip.tcl` criam e configuram esses IPs no Vivado e geram os arquivos de síntese e simulação. DSPs são blocos da FPGA dedicados a operações aritméticas.

## `Codigos_C_HLS/`

Todos os códigos calculam `a × b + c` e escrevem a saída em `*result`. As diretivas `ap_none` definem portas de dados sem sinais de handshake; `ap_ctrl_none` dispensa o protocolo de controle de início e término da função. Essas interfaces, por si só, não eliminam clock nem registradores.

| Arquivo | Função e versão gerada |
| --- | --- |
| `mac_float.cpp` | Versão básica com `float`, separando produto (`mult`) e soma (`acc`), sem diretivas adicionais para os operadores. Origina `mac_float/`. |
| `mac_float_simp.cpp` | Expressa o cálculo diretamente como `(a * b) + c`, sem variáveis intermediárias explícitas. Origina `mac_float_simp/`. |
| `mac_float_comb.cpp` | Adiciona `LATENCY min=0 max=0`, solicitando latência zero para a função. Origina `mac_float_comb/`, cujo VHDL gerado ainda possui registradores e latência informada de 9 ciclos. |
| `mac_float_comb_dsp.cpp` | Usa `BIND_OP` para selecionar `maxdsp` na multiplicação e `fulldsp` na soma, sem fixar a latência dos operadores. Origina `mac_float_comb_dsp/`. |
| `mac_float_comb_dsp_latency0.cpp` | Combina `LATENCY min=0 max=0` com `BIND_OP` e `latency=0` nos dois operadores, mantendo as escolhas de DSPs. Origina a versão combinacional `mac_float_comb_dsp_latency0/`. |
| `mac_float_pipeline.cpp` | Usa `PIPELINE II=1` para solicitar o início de uma operação por ciclo. Origina `mac_float_pipeline/`, com registradores para alinhar os dados. |
| `mac_int.cpp` | Calcula a expressão com entradas e saída do tipo `int`, em vez de `float`. Origina `mac_int/`, com aritmética de 32 bits no VHDL gerado. |

As diretivas expressam as solicitações ao HLS; o circuito efetivamente gerado é descrito nas pastas abaixo. Em particular, a solicitação de latência zero em `mac_float_comb.cpp` não corresponde à latência registrada no VHDL disponível.

## `mac_float/`

Versão com máquina de estados e registrador entre multiplicação e soma. O cabeçalho gerado pelo Vitis HLS informa latência de 10 ciclos.

| Arquivo | Função |
| --- | --- |
| `mac_float.vhd` | Módulo principal: conecta multiplicador e somador e controla o registro do produto. |
| `mac_float_fadd_32ns_32ns_32_7_full_dsp_1.vhd` | Adaptador do somador de ponto flutuante, com registros de entrada e controle de habilitação. |
| `mac_float_fadd_32ns_32ns_32_7_full_dsp_1_ip.tcl` | Configura a IP de soma com uso de DSPs (`Full_Usage`) e latência interna de 5 ciclos. |
| `mac_float_fmul_32ns_32ns_32_4_max_dsp_1.vhd` | Adaptador do multiplicador de ponto flutuante, com registros de entrada e habilitação. |
| `mac_float_fmul_32ns_32ns_32_4_max_dsp_1_ip.tcl` | Configura a IP de multiplicação com uso máximo de DSPs (`Max_Usage`) e latência interna de 2 ciclos. |

## `mac_float_comb/`

Apesar do nome `comb`, o circuito contém clock, máquina de estados e registradores. A soma é configurada sem DSPs, e o cabeçalho HLS informa latência total de 9 ciclos.

| Arquivo | Função |
| --- | --- |
| `mac_float_comb.vhd` | Módulo principal: registra o produto de `a` e `b` e o encaminha à soma com `c`. |
| `mac_float_comb_fadd_32ns_32ns_32_6_no_dsp_1.vhd` | Adaptador com registros para a IP de soma sem DSPs. |
| `mac_float_comb_fadd_32ns_32ns_32_6_no_dsp_1_ip.tcl` | Configura o somador com `No_Usage` de DSPs e latência interna de 4 ciclos. |
| `mac_float_comb_fmul_32ns_32ns_32_4_max_dsp_1.vhd` | Adaptador com registros para a IP de multiplicação. |
| `mac_float_comb_fmul_32ns_32ns_32_4_max_dsp_1_ip.tcl` | Configura o multiplicador com `Max_Usage` de DSPs e latência interna de 2 ciclos. |

## `mac_float_comb_dsp/`

Versão com DSPs habilitados nos dois operadores. Também possui clock, máquina de estados e registradores, com latência de 10 ciclos informada pelo HLS.

| Arquivo | Função |
| --- | --- |
| `mac_float_comb_dsp.vhd` | Módulo principal: coordena a multiplicação, o registro intermediário e a soma com `c`. |
| `mac_float_comb_dsp_fadd_32ns_32ns_32_7_full_dsp_1.vhd` | Adaptador com registros para o somador de ponto flutuante. |
| `mac_float_comb_dsp_fadd_32ns_32ns_32_7_full_dsp_1_ip.tcl` | Configura a soma com `Full_Usage` de DSPs e latência interna de 5 ciclos. |
| `mac_float_comb_dsp_fmul_32ns_32ns_32_4_max_dsp_1.vhd` | Adaptador com registros para o multiplicador de ponto flutuante. |
| `mac_float_comb_dsp_fmul_32ns_32ns_32_4_max_dsp_1_ip.tcl` | Configura a multiplicação com `Max_Usage` de DSPs e latência interna de 2 ciclos. |

## `mac_float_comb_dsp_latency0/`

Versão combinacional: multiplicador e somador são ligados diretamente, sem clock. As IPs têm latência configurada em zero ciclos, mas o resultado ainda depende do atraso de propagação do circuito. A entrada `ap_rst` existe no módulo principal, porém não é utilizada.

| Arquivo | Função |
| --- | --- |
| `mac_float_comb_dsp_latency0.vhd` | Módulo principal: liga `a × b` diretamente ao somador com `c`, sem registradores intermediários. |
| `mac_float_comb_dsp_latency0_fadd_32ns_32ns_32_1_full_dsp_1.vhd` | Adaptador combinacional do somador, sem clock nem registros. |
| `mac_float_comb_dsp_latency0_fadd_32ns_32ns_32_1_full_dsp_1_ip.tcl` | Configura a soma com `Full_Usage` de DSPs e latência interna zero. |
| `mac_float_comb_dsp_latency0_fmul_32ns_32ns_32_1_max_dsp_1.vhd` | Adaptador combinacional do multiplicador, sem clock nem registros. |
| `mac_float_comb_dsp_latency0_fmul_32ns_32ns_32_1_max_dsp_1_ip.tcl` | Configura a multiplicação com `Max_Usage` de DSPs e latência interna zero. |

## `mac_float_pipeline/`

Versão em pipeline, com latência de 10 ciclos e intervalo de iniciação de 1 ciclo informados pelo HLS: permite iniciar uma operação por ciclo. Registradores atrasam `c` para alinhá-lo ao produto correspondente.

| Arquivo | Função |
| --- | --- |
| `mac_float_pipeline.vhd` | Módulo principal: conecta os operadores e os registradores que alinham os dados no pipeline. |
| `mac_float_pipeline_fadd_32ns_32ns_32_7_full_dsp_1.vhd` | Adaptador com registros para o somador do pipeline. |
| `mac_float_pipeline_fadd_32ns_32ns_32_7_full_dsp_1_ip.tcl` | Configura a soma com `Full_Usage` de DSPs e latência interna de 5 ciclos. |
| `mac_float_pipeline_fmul_32ns_32ns_32_4_max_dsp_1.vhd` | Adaptador com registros para o multiplicador do pipeline. |
| `mac_float_pipeline_fmul_32ns_32ns_32_4_max_dsp_1_ip.tcl` | Configura a multiplicação com `Max_Usage` de DSPs e latência interna de 2 ciclos. |

## `mac_float_simp/`

Nos arquivos gerados, esta versão mantém a mesma estrutura básica de `mac_float`: máquina de estados, produto registrado e soma com `c`. A latência informada pelo HLS é de 10 ciclos.

| Arquivo | Função |
| --- | --- |
| `mac_float_simp.vhd` | Módulo principal: controla o registro do produto e sua conexão ao somador. |
| `mac_float_simp_fadd_32ns_32ns_32_7_full_dsp_1.vhd` | Adaptador com registros para a IP de soma. |
| `mac_float_simp_fadd_32ns_32ns_32_7_full_dsp_1_ip.tcl` | Configura a soma com `Full_Usage` de DSPs e latência interna de 5 ciclos. |
| `mac_float_simp_fmul_32ns_32ns_32_4_max_dsp_1.vhd` | Adaptador com registros para a IP de multiplicação. |
| `mac_float_simp_fmul_32ns_32ns_32_4_max_dsp_1_ip.tcl` | Configura a multiplicação com `Max_Usage` de DSPs e latência interna de 2 ciclos. |

## `mac_int/`

Versão inteira, com máquina de estados e latência de 2 ciclos informada pelo HLS. A multiplicação interpreta as entradas como inteiros com sinal e mantém os 32 bits inferiores do produto; a soma também tem saída limitada a 32 bits.

| Arquivo | Função |
| --- | --- |
| `mac_int.vhd` | Módulo principal: registra o produto e realiza a soma com `c` diretamente em VHDL. |
| `mac_int_mul_32s_32s_32_2_1.vhd` | Implementa o multiplicador inteiro com sinal, truncamento para a largura de saída e registro habilitado por `ce`. |

Esta pasta não contém arquivos `.tcl`: a aritmética está descrita diretamente nos arquivos VHDL.

> As latências internas dos scripts Tcl pertencem apenas às IPs; as latências totais citadas vêm dos cabeçalhos HLS dos módulos principais. Os números nos nomes dos arquivos não devem ser usados isoladamente como medida da latência total.
