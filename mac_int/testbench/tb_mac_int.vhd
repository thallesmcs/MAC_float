library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

entity tb_mac_int is
end entity;

architecture sim of tb_mac_int is
  constant ARQUITETURA     : string   := "mac_int";
  constant PERIODO         : time     := 10 ns;
  constant ATRASO_AMOSTRA  : time     := 1 ns;
  constant N_VETORES       : positive := 8;
  constant INTERVALO       : positive := 3;
  constant MAX_CICLOS      : natural  := 128;

  subtype word is std_logic_vector(31 downto 0);
  type integer_array_t is array (natural range <>) of integer;

  constant A_VAL : integer_array_t := (2, -1, 5, -3, 7, 4, -2, 6);
  constant B_VAL : integer_array_t := (3, 4, 2, -2, 1, -2, 5, 2);
  constant PRODUTO_VAL : integer_array_t := (6, -4, 10, 6, 7, -8, -10, 12);
  constant ESPERADO_VAL : integer_array_t := (6, 2, 12, 18, 25, 17, 7, 19);

  signal ap_clk   : std_logic := '0';
  signal ap_rst   : std_logic := '1';
  signal a        : word := (others => '0');
  signal b        : word := (others => '0');
  signal result   : word;
  signal terminou : boolean := false;

  function int_string(x : word) return string is
  begin
    if is_x(x) then
      return "INDEFINIDO";
    end if;
    return integer'image(to_integer(signed(x)));
  end function;

begin
  ap_clk <= not ap_clk after PERIODO/2 when not terminou else '0';

  dut : entity work.mac_int
    port map (
      ap_clk => ap_clk,
      ap_rst => ap_rst,
      a      => a,
      b      => b,
      result => result
    );

  estimulos : process
    file csv : text open write_mode is "mac_int/testbench/mac_int_output.csv";
    variable l                 : line;
    variable indice_entrada    : natural := 0;
    variable indice_saida      : natural := 0;
    variable ciclo             : natural := 0;
    variable ciclo_entrada     : natural := 0;
    variable falhas            : natural := 0;
    variable esperado_bits     : word;

    procedure escrever_linha(
      idx       : natural;
      c_entrada : natural;
      c_saida   : natural;
      ok        : boolean
    ) is
      variable exp_bits : word;
    begin
      exp_bits := std_logic_vector(to_signed(ESPERADO_VAL(idx), 32));

      write(l, ARQUITETURA & ",");
      write(l, integer'image(idx) & ",");
      write(l, integer'image(A_VAL(idx)) & ",");
      write(l, integer'image(B_VAL(idx)) & ",");
      write(l, integer'image(PRODUTO_VAL(idx)) & ",");
      write(l, integer'image(ESPERADO_VAL(idx)) & ",");
      write(l, int_string(result) & ",");
      write(l, to_hstring(result) & ",");
      write(l, to_hstring(exp_bits) & ",");
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

    ap_rst <= '1';
    a <= (others => '0');
    b <= (others => '0');

    for k in 1 to 4 loop
      wait until rising_edge(ap_clk);
    end loop;

    wait until falling_edge(ap_clk);
    ap_rst <= '0';
    a <= std_logic_vector(to_signed(A_VAL(0), 32));
    b <= std_logic_vector(to_signed(B_VAL(0), 32));

    indice_entrada := 0;
    indice_saida   := 0;
    ciclo          := 0;

    while indice_saida < N_VETORES and ciclo <= MAX_CICLOS loop
      wait until rising_edge(ap_clk);
      wait for ATRASO_AMOSTRA;

      esperado_bits := std_logic_vector(to_signed(ESPERADO_VAL(indice_saida), 32));

      if not is_x(result) and result = esperado_bits then
        ciclo_entrada := indice_saida * INTERVALO;
        escrever_linha(indice_saida, ciclo_entrada, ciclo, true);
        indice_saida := indice_saida + 1;
      end if;

      exit when indice_saida = N_VETORES;

      wait until falling_edge(ap_clk);

      if ((ciclo + 1) mod INTERVALO = 0) and
         (indice_entrada < N_VETORES - 1) then
        indice_entrada := indice_entrada + 1;
        a <= std_logic_vector(to_signed(A_VAL(indice_entrada), 32));
        b <= std_logic_vector(to_signed(B_VAL(indice_entrada), 32));
      end if;

      ciclo := ciclo + 1;
    end loop;

    if indice_saida < N_VETORES then
      ciclo_entrada := indice_saida * INTERVALO;
      escrever_linha(indice_saida, ciclo_entrada, ciclo, false);
      falhas := falhas + 1;
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
