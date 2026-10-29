library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.float_pkg.all;
use std.textio.all;

entity tb_mac_float_comb_dsp_latency0 is
end entity;

architecture sim of tb_mac_float_comb_dsp_latency0 is
  constant ARQUITETURA     : string   := "mac_float_comb_dsp_latency0";
  constant PERIODO         : time     := 10 ns;
  constant ATRASO_AMOSTRA  : time     := 1 ns;
  constant N_VETORES       : positive := 8;
  constant INTERVALO       : positive := 1;
  constant LATENCIA_ZERO   : boolean  := true;
  constant MAX_CICLOS      : natural  := 256;

  subtype word is std_logic_vector(31 downto 0);
  type word_array_t is array (natural range <>) of word;
  type integer_array_t is array (natural range <>) of integer;

  constant A_VAL : integer_array_t := (2, -1, 5, -3, 7, 4, -2, 6);
  constant B_VAL : integer_array_t := (3, 4, 2, -2, 1, -2, 5, 2);
  constant PRODUTO_VAL : integer_array_t := (6, -4, 10, 6, 7, -8, -10, 12);
  constant ESPERADO_VAL : integer_array_t := (6, 2, 12, 18, 25, 17, 7, 19);

  constant A_BITS : word_array_t := (
    x"40000000", x"BF800000", x"40A00000", x"C0400000", x"40E00000", x"40800000", x"C0000000", x"40C00000"
  );
  constant B_BITS : word_array_t := (
    x"40400000", x"40800000", x"40000000", x"C0000000", x"3F800000", x"C0000000", x"40A00000", x"40000000"
  );
  constant ESPERADO_BITS : word_array_t := (
    x"40C00000", x"40000000", x"41400000", x"41900000", x"41C80000", x"41880000", x"40E00000", x"41980000"
  );

  signal ap_clk   : std_logic := '0';
  signal ap_rst   : std_logic := '1';
  signal a        : word := (others => '0');
  signal b        : word := (others => '0');
  signal result   : word;
  signal terminou : boolean := false;

  function fp_string(x : word) return string is
  begin
    if is_x(x) then
      return "INDEFINIDO";
    end if;
    return real'image(to_real(to_float(x, 8, 23)));
  end function;

begin
  ap_clk <= not ap_clk after PERIODO/2 when not terminou else '0';

  dut : entity work.mac_float_comb_dsp_latency0
    port map (
      ap_clk => ap_clk,
      ap_rst => ap_rst,
      a      => a,
      b      => b,
      result => result
    );

  estimulos : process
    file csv : text open write_mode is "mac_float_comb_dsp_latency0/testbench/mac_float_comb_dsp_latency0_output.csv";
    variable l                 : line;
    variable indice_entrada    : natural := 0;
    variable indice_saida      : natural := 0;
    variable ciclo             : natural := 0;
    variable ciclo_entrada     : natural := 0;
    variable latencia_observada: natural := 0;
    variable falhas            : natural := 0;

    procedure escrever_linha(
      idx       : natural;
      c_entrada : natural;
      c_saida   : natural;
      ok        : boolean
    ) is
    begin
      write(l, ARQUITETURA & ",");
      write(l, integer'image(idx) & ",");
      write(l, integer'image(A_VAL(idx)) & ",");
      write(l, integer'image(B_VAL(idx)) & ",");
      write(l, integer'image(PRODUTO_VAL(idx)) & ",");
      write(l, integer'image(ESPERADO_VAL(idx)) & ",");
      write(l, fp_string(result) & ",");
      write(l, to_hstring(result) & ",");
      write(l, to_hstring(ESPERADO_BITS(idx)) & ",");
      write(l, integer'image(c_entrada) & ",");
      write(l, integer'image(c_saida) & ",");
      write(l, integer'image(c_saida - c_entrada) & ",");
      if idx = N_VETORES - 1 then
        write(l, string'("SIM,"));
        write(l, integer'image(c_saida) & ",");
      else
        write(l, string'("NAO,,"));
      end if;
      if ok then
        write(l, string'("PASS"));
      else
        write(l, string'("FAIL"));
      end if;
      writeline(csv, l);
    end procedure;

  begin
    write(l, string'(
      "arquitetura,id_teste,a,b,produto,esperado_acumulado,saida,saida_hex," &
      "esperado_hex,ciclo_entrada,ciclo_saida,latencia_observada_ciclos," &
      "resultado_final,ciclos_ate_resultado_final,status"
    ));
    writeline(csv, l);

    -- O acumulador 'static' gerado pelo HLS inicia em zero.
    -- Mantemos a=b=0 durante o reset para que arquiteturas cujo ACC nao
    -- recebe reset explicito nao alterem o estado.
    ap_rst <= '1';
    a <= (others => '0');
    b <= (others => '0');

    for k in 1 to 4 loop
      wait until rising_edge(ap_clk);
    end loop;

    wait until falling_edge(ap_clk);
    ap_rst <= '0';
    a <= A_BITS(0);
    b <= B_BITS(0);

    if LATENCIA_ZERO then
      -- A versao latency0 apresenta next_acc combinacionalmente.
      -- Amostramos antes da borda que grava esse valor em ACC.
      for idx in 0 to N_VETORES - 1 loop
        if idx > 0 then
          wait until rising_edge(ap_clk);  -- grava o ACC da operacao anterior
          wait until falling_edge(ap_clk);
          a <= A_BITS(idx);
          b <= B_BITS(idx);
        end if;

        wait for ATRASO_AMOSTRA;

        if not is_x(result) and result = ESPERADO_BITS(idx) then
          escrever_linha(idx, idx, idx, true);
        else
          escrever_linha(idx, idx, idx, false);
          falhas := falhas + 1;
        end if;
      end loop;

    else
      -- As demais arquiteturas recebem novos operandos a cada INTERVALO
      -- de iniciacao efetivamente gerado no RTL.
      indice_entrada := 0;
      indice_saida   := 0;
      ciclo          := 0;

      while indice_saida < N_VETORES and ciclo <= MAX_CICLOS loop
        wait until rising_edge(ap_clk);
        wait for ATRASO_AMOSTRA;

        -- Detecta o ciclo real em que o proximo acumulado esperado aparece.
        if not is_x(result) and result = ESPERADO_BITS(indice_saida) then
          ciclo_entrada      := indice_saida * INTERVALO;
          latencia_observada := ciclo - ciclo_entrada;
          escrever_linha(indice_saida, ciclo_entrada, ciclo, true);
          indice_saida := indice_saida + 1;
        end if;

        exit when indice_saida = N_VETORES;

        wait until falling_edge(ap_clk);

        -- Troca de vetor imediatamente antes da proxima iniciacao.
        if ((ciclo + 1) mod INTERVALO = 0) and
           (indice_entrada < N_VETORES - 1) then
          indice_entrada := indice_entrada + 1;
          a <= A_BITS(indice_entrada);
          b <= B_BITS(indice_entrada);
        end if;

        ciclo := ciclo + 1;
      end loop;

      if indice_saida < N_VETORES then
        -- Timeout: registra o primeiro acumulado que nao apareceu.
        ciclo_entrada := indice_saida * INTERVALO;
        escrever_linha(indice_saida, ciclo_entrada, ciclo, false);
        falhas := falhas + 1;
      end if;
    end if;

    file_close(csv);

    if falhas = 0 then
      report ARQUITETURA & ": PASS; resultado final = " &
             integer'image(ESPERADO_VAL(N_VETORES-1))
        severity note;
    else
      report ARQUITETURA & ": FAIL; falhas = " & integer'image(falhas)
        severity error;
    end if;

    terminou <= true;
    wait;
  end process;

end architecture;
