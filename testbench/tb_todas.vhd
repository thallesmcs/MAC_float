entity tb_todas is
  generic (RAIZ : string := ".");
end entity;
architecture sim of tb_todas is
begin
  u_mac_float : entity work.tb_mac_float generic map (RAIZ => RAIZ);
  u_mac_float_simp : entity work.tb_mac_float_simp generic map (RAIZ => RAIZ);
  u_mac_float_comb : entity work.tb_mac_float_comb generic map (RAIZ => RAIZ);
  u_mac_float_comb_dsp : entity work.tb_mac_float_comb_dsp generic map (RAIZ => RAIZ);
  u_mac_float_comb_dsp_latency0 : entity work.tb_mac_float_comb_dsp_latency0 generic map (RAIZ => RAIZ);
  u_mac_float_pipeline : entity work.tb_mac_float_pipeline generic map (RAIZ => RAIZ);
  u_mac_int : entity work.tb_mac_int generic map (RAIZ => RAIZ);
end architecture;
