-- Banco unico de estimulos, verificacao e medicao para TODAS as arquiteturas.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.float_pkg.all;
use std.textio.all;

entity tb_mac_comum is
  generic (
    NOME : string;
    INTEIRO : boolean := false;
    LATENCIA : natural;
    INTERVALO : positive;
    VETORES : string;
    CSV_SAIDA : string;
    CSV_FLUXO : string
  );
  port (
    ap_clk : out std_logic := '0';
    ap_rst : out std_logic := '1';
    a, b, c : out std_logic_vector(31 downto 0) := (others => '0');
    result : in std_logic_vector(31 downto 0)
  );
end entity;

architecture sim of tb_mac_comum is
  constant PERIODO : time := 10 ns;
  -- Primitivas UNISIM incluem atrasos funcionais (ex.: DSP48E1), mesmo sem
  -- registradores. A mesma margem de acomodacao e usada em todos os DUTs.
  constant ATRASO_AMOSTRA : time := 1 ns;
  constant JANELA : positive := 32;
  constant MAX_VETORES : positive := 1024;
  subtype word is std_logic_vector(31 downto 0);
  type vetor_t is record
    a, b, c, esperado : word;
  end record;
  type vetores_t is array (natural range <>) of vetor_t;
  type words_t is array (natural range <>) of word;
  signal terminou : boolean := false;

  function valor(x : word) return string is
  begin
    if is_x(x) then return "INDEFINIDO"; end if;
    if INTEIRO then return integer'image(to_integer(signed(x))); end if;
    return real'image(to_real(to_float(x, 8, 23)));
  end function;
begin
  ap_clk <= not ap_clk after PERIODO/2 when not terminou else '0';

  estimulos : process
    file entrada : text open read_mode is VETORES;
    file saida : text open write_mode is CSV_SAIDA;
    file fluxo : text open write_mode is CSV_FLUXO;
    variable l, linha : line;
    variable dados : vetores_t(0 to MAX_VETORES-1);
    variable total : natural := 0;
    variable ai, bi, ci : integer;
    variable af, bf, cf, ef, ei : word;
    variable anterior, inicial, capturado : word;
    variable vistos : words_t(0 to JANELA);
    variable distintos, mudancas, indefinidos, falhas, falhas_fluxo : natural := 0;
    variable ultimo_incorreto : integer;
    variable repetido, correto : boolean;
    variable inicio, tempo_captura : time;
    variable indice, enviado : natural;
    procedure coluna(variable destino : inout line; texto : string) is
    begin
      write(destino, texto); write(destino, string'(","));
    end procedure;
    procedure aplicar(v : vetor_t) is
    begin a <= v.a; b <= v.b; c <= v.c; end procedure;
    procedure amostrar(ciclo : natural; esperado : word) is
    begin
      if result /= esperado or is_x(result) then
        ultimo_incorreto := ciclo;
      end if;
      if ciclo = LATENCIA then
        capturado := result;
        tempo_captura := now - inicio;
      end if;
      -- Verifica toda a janela, mesmo se a resposta aparecer antes por coincidencia.
      if ciclo >= LATENCIA and (is_x(result) or result /= esperado) then
        correto := false;
      end if;
      if ciclo < LATENCIA then
        if is_x(result) then
          indefinidos := indefinidos + 1;
        elsif result /= esperado and result /= inicial then
          repetido := false;
          for k in 0 to integer(distintos)-1 loop
            if vistos(k) = result then repetido := true; end if;
          end loop;
          if not repetido then
            vistos(distintos) := result; distintos := distintos + 1;
          end if;
        end if;
        if result /= anterior then mudancas := mudancas + 1; end if;
      end if;
      anterior := result;
    end procedure;
  begin
    assert LATENCIA < JANELA report "Latencia excede a janela comum" severity failure;
    while not endfile(entrada) loop
      assert total < MAX_VETORES report "Excesso de vetores" severity failure;
      readline(entrada, l);
      read(l, ai); read(l, bi); read(l, ci);
      hread(l, af); hread(l, bf); hread(l, cf); hread(l, ef); hread(l, ei);
      if INTEIRO then
        dados(total) := (std_logic_vector(to_signed(ai,32)),
                        std_logic_vector(to_signed(bi,32)),
                        std_logic_vector(to_signed(ci,32)), ei);
      else
        dados(total) := (af, bf, cf, ef);
      end if;
      total := total + 1;
    end loop;
    assert total > 0 report "Arquivo de vetores vazio" severity failure;
    write(l, string'("nome_arquitetura,valor_entrada_a,valor_entrada_b,valor_entrada_c,valor_saida,id_teste,valor_esperado,a_hex,b_hex,c_hex,saida_hex,esperado_hex,ciclos_ate_resultado,ciclos_estabilizacao_observada,valores_intermediarios_observados,mudancas_antes_resposta,amostras_indefinidas,tempo_ate_amostra_ns,periodo_clock_ns,status"));
    writeline(saida,l);
    write(l, string'("nome_arquitetura,id_teste,intervalo_entrada_ciclos,ciclo_saida,saida_hex,esperado_hex,status"));
    writeline(fluxo,l);

    for teste in 0 to total-1 loop
      -- Reset + drenagem iguais para todos; nao entram na latencia medida.
      ap_rst <= '1'; a <= (others=>'0'); b <= (others=>'0'); c <= (others=>'0');
      for k in 1 to JANELA loop wait until rising_edge(ap_clk); wait for ATRASO_AMOSTRA; end loop;
      wait until falling_edge(ap_clk);
      ap_rst <= '0'; aplicar(dados(teste));
      inicio := now; inicial := result; anterior := result;
      distintos := 0; mudancas := 0; indefinidos := 0;
      ultimo_incorreto := -1; correto := true;
      wait for ATRASO_AMOSTRA;
      amostrar(0, dados(teste).esperado);
      for ciclo in 1 to JANELA loop
        wait until rising_edge(ap_clk); wait for ATRASO_AMOSTRA;
        amostrar(ciclo, dados(teste).esperado);
      end loop;
      coluna(l,NOME); coluna(l,valor(dados(teste).a)); coluna(l,valor(dados(teste).b));
      coluna(l,valor(dados(teste).c)); coluna(l,valor(capturado));
      coluna(l,integer'image(teste)); coluna(l,valor(dados(teste).esperado));
      coluna(l,to_hstring(dados(teste).a)); coluna(l,to_hstring(dados(teste).b));
      coluna(l,to_hstring(dados(teste).c)); coluna(l,to_hstring(capturado));
      coluna(l,to_hstring(dados(teste).esperado));
      coluna(l,integer'image(LATENCIA));
      if ultimo_incorreto = JANELA then coluna(l,"NAO_ESTABILIZOU");
      else coluna(l,integer'image(ultimo_incorreto+1)); end if;
      coluna(l,integer'image(distintos)); coluna(l,integer'image(mudancas));
      coluna(l,integer'image(indefinidos));
      coluna(l,real'image(real(tempo_captura / 1 ps)/1000.0));
      coluna(l,"10");
      if correto then write(l,string'("PASS"));
      else write(l,string'("FAIL")); falhas := falhas+1; end if;
      writeline(saida,l);
    end loop;

    -- Segunda fase: mesmos vetores consecutivos, no intervalo de cada DUT.
    -- FSM: mantem a,b,c ate a proxima operacao; pipeline: troca a cada ciclo.
    ap_rst <= '1'; a <= (others=>'0'); b <= (others=>'0'); c <= (others=>'0');
    for k in 1 to JANELA loop wait until rising_edge(ap_clk); wait for ATRASO_AMOSTRA; end loop;
    wait until falling_edge(ap_clk);
    ap_rst <= '0'; aplicar(dados(0)); enviado := 1;
    if LATENCIA = 0 then
      for teste in 0 to total-1 loop
        aplicar(dados(teste)); wait for ATRASO_AMOSTRA;
        coluna(l,NOME); coluna(l,integer'image(teste)); coluna(l,"0"); coluna(l,"0");
        coluna(l,to_hstring(result)); coluna(l,to_hstring(dados(teste).esperado));
        if result = dados(teste).esperado and not is_x(result) then write(l,string'("PASS"));
        else write(l,string'("FAIL")); falhas_fluxo := falhas_fluxo+1; end if;
        writeline(fluxo,l);
        wait for PERIODO - ATRASO_AMOSTRA;
      end loop;
    else
      for ciclo in 1 to (total-1)*INTERVALO+LATENCIA loop
        wait until rising_edge(ap_clk); wait for ATRASO_AMOSTRA;
        if ciclo >= LATENCIA and (ciclo-LATENCIA) mod INTERVALO = 0 then
          indice := (ciclo-LATENCIA)/INTERVALO;
          coluna(l,NOME); coluna(l,integer'image(indice));
          coluna(l,integer'image(INTERVALO)); coluna(l,integer'image(ciclo));
          coluna(l,to_hstring(result)); coluna(l,to_hstring(dados(indice).esperado));
          if result = dados(indice).esperado and not is_x(result) then write(l,string'("PASS"));
          else write(l,string'("FAIL")); falhas_fluxo := falhas_fluxo+1; end if;
          writeline(fluxo,l);
        end if;
        wait until falling_edge(ap_clk);
        if ciclo mod INTERVALO = 0 and enviado < total then
          aplicar(dados(enviado)); enviado := enviado+1;
        end if;
      end loop;
    end if;
    file_close(saida); file_close(fluxo); file_close(entrada);
    report NOME & ": testes=" & integer'image(total) &
      " falhas=" & integer'image(falhas) & " falhas_fluxo=" & integer'image(falhas_fluxo);
    assert falhas = 0 and falhas_fluxo = 0 report NOME & ": falha funcional" severity error;
    terminou <= true;
    wait;
  end process;
end architecture;
