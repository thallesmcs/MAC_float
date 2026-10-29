-- Gerado por testbench/executar.py. Somente adaptacao de interface/parametros.
library ieee;
use ieee.std_logic_1164.all;
entity tb_mac_float_comb_dsp is
  generic (RAIZ : string := ".");
end entity;
architecture sim of tb_mac_float_comb_dsp is
  signal clk, rst : std_logic;
  signal a, b, c, resultado : std_logic_vector(31 downto 0);
begin
  dut : entity work.mac_float_comb_dsp
    port map (ap_clk => clk, ap_rst => rst, a => a, b => b, c => c, result => resultado);
  banco : entity work.tb_mac_comum
    generic map (
      NOME => "mac_float_comb_dsp", INTEIRO => false,
      LATENCIA => 10, INTERVALO => 11,
      VETORES => RAIZ & "/testbench/vetores.txt",
      CSV_SAIDA => RAIZ & "/mac_float_comb_dsp/testbench/mac_float_comb_dsp_output.csv",
      CSV_FLUXO => RAIZ & "/mac_float_comb_dsp/testbench/mac_float_comb_dsp_fluxo.csv")
    port map (ap_clk => clk, ap_rst => rst, a => a, b => b, c => c, result => resultado);
end architecture;
