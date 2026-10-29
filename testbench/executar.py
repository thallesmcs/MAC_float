# python testbench/executar.py --resumir

"""Gera os mesmos estimulos e simula o RTL com as IPs originais no Vivado."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import struct
import subprocess
import sys

RAIZ = Path(__file__).resolve().parents[1]
ARQUITETURAS = (
    "mac_float", "mac_float_simp", "mac_float_comb", "mac_float_comb_dsp",
    "mac_float_comb_dsp_latency0", "mac_float_pipeline", "mac_int",
)


def f32(x):
    return struct.unpack(">f", struct.pack(">f", x))[0]


def hex_float(x):
    return struct.pack(">f", x).hex().upper()


def metadados(nome):
    texto = (RAIZ / nome / f"{nome}.vhd").read_text(encoding="utf-8")
    latencia = int(re.search(r"HLS_SYN_LAT=(\d+)", texto)[1])
    tem_clock = bool(re.search(r"ap_clk\s*:\s*IN", texto, re.I))
    pipeline = "HLS_INPUT_ARCH=pipeline" in texto
    # FSMs presentes no RTL percorrem LATENCIA+1 estados, sem handshake.
    if tem_clock and not pipeline:
        estados = re.findall(r"constant ap_ST_fsm_state\d+\s*:", texto)
        intervalo = len(estados)
        if intervalo != latencia + 1:
            raise ValueError(f"{nome}: revisar intervalo da FSM")
    else:
        intervalo = 1 if pipeline else 0
    return dict(nome=nome, latencia=latencia, intervalo=intervalo,
                tem_clock=tem_clock, inteiro=nome == "mac_int")


def gerar_vetores():
    # Todos os operandos sao inteiros exatamente representaveis em binary32.
    # Inclui zeros, sinais, cancelamento, arredondamento e overflow inteiro.
    valores = [
        (1, 2, 3), (0, 5, 7), (5, 0, -7), (0, 0, 0), (-2, 3, 4),
        (-2, -3, -4), (1, 1, -1), (1, 1, -1), (9, 11, -99),
        (16777216, 1, 1), (16777215, 1, 2), (4097, 4097, -16777216),
        (65536, 65536, 0), (65537, 65537, -1), (-65536, 65536, 1),
        (16777216, 16777216, -16777216), (-16777216, 16777216, 16777216),
        (3, 5592405, 1), (12345, -54321, 16777215), (1, 1, 0),
    ]
    rng = random.Random(20261029)
    for _ in range(76):
        limite = rng.choice([16, 4096, 65536, 16777216])
        valores.append(tuple(rng.randint(-limite, limite) for _ in range(3)))
    linhas = []
    for a, b, c in valores:
        # Duas operacoes binary32, NAO uma FMA de arredondamento unico.
        esperado = f32(f32(f32(a) * f32(b)) + f32(c))
        inteiro = (a * b + c) & 0xFFFFFFFF
        linhas.append(f"{a} {b} {c} {hex_float(a)} {hex_float(b)} {hex_float(c)} "
                      f"{hex_float(esperado)} {inteiro:08X}\n")
    (RAIZ / "testbench/vetores.txt").write_text("".join(linhas), encoding="ascii")
    return len(valores)


def gerar_adaptador(meta):
    nome = meta["nome"]
    pasta = RAIZ / nome / "testbench"
    pasta.mkdir(exist_ok=True)
    arquivo = pasta / f"tb_{nome}.vhd"
    clock = "ap_clk => clk, " if meta["tem_clock"] else ""
    arquivo.write_text(f'''-- Gerado por testbench/executar.py. Somente adaptacao de interface/parametros.
library ieee;
use ieee.std_logic_1164.all;
entity tb_{nome} is
  generic (RAIZ : string := ".");
end entity;
architecture sim of tb_{nome} is
  signal clk, rst : std_logic;
  signal a, b, c, resultado : std_logic_vector(31 downto 0);
begin
  dut : entity work.{nome}
    port map ({clock}ap_rst => rst, a => a, b => b, c => c, result => resultado);
  banco : entity work.tb_mac_comum
    generic map (
      NOME => "{nome}", INTEIRO => {str(meta["inteiro"]).lower()},
      LATENCIA => {meta["latencia"]}, INTERVALO => {max(1, meta["intervalo"])},
      VETORES => RAIZ & "/testbench/vetores.txt",
      CSV_SAIDA => RAIZ & "/{nome}/testbench/{nome}_output.csv",
      CSV_FLUXO => RAIZ & "/{nome}/testbench/{nome}_fluxo.csv")
    port map (ap_clk => clk, ap_rst => rst, a => a, b => b, c => c, result => resultado);
end architecture;
''', encoding="utf-8")
    return arquivo


def tcl_path(path):
    # Tcl braces protegem espacos e substituicoes; caminhos com chaves sao rejeitados.
    path = Path(path).as_posix()
    if any(c in path for c in "{}\n\r"):
        raise ValueError("Caminho nao suportado pelo Tcl")
    return "{" + path + "}"


def preparar(nomes):
    quantidade = gerar_vetores()
    metas = [metadados(n) for n in nomes]
    fontes = [RAIZ / "testbench/tb_mac_comum.vhd"]
    ips = []
    for meta in metas:
        fontes.extend(sorted((RAIZ / meta["nome"]).glob("*.vhd")))
        ips.extend(sorted((RAIZ / meta["nome"]).glob("*_ip.tcl")))
        fontes.append(gerar_adaptador(meta))
    top = RAIZ / "testbench/tb_todas.vhd"
    top.write_text('entity tb_todas is\n  generic (RAIZ : string := ".");\nend entity;\n'
                   'architecture sim of tb_todas is\nbegin\n' + "".join(
                       f'  u_{n} : entity work.tb_{n} generic map (RAIZ => RAIZ);\n'
                       for n in nomes) + 'end architecture;\n', encoding="utf-8")
    fontes.append(top)
    digest = hashlib.sha256()
    for f in fontes + ips:
        digest.update(f.name.encode()); digest.update(f.read_bytes())
    build = RAIZ / "testbench/.sim" / digest.hexdigest()[:12]
    build.mkdir(parents=True, exist_ok=True)
    script = build / "simular.tcl"
    projeto = build / "projeto/mac_testbench.xpr"
    comandos = [
        f"cd {tcl_path(build)}",
        f"if {{[file exists {tcl_path(projeto)}]}} {{",
        f"  open_project {tcl_path(projeto)}",
        "} else {",
        f"  create_project mac_testbench {tcl_path(projeto.parent)} -part xc7s50csga324-1",
        "  set_property target_language VHDL [current_project]",
    ]
    comandos += [f"  source {tcl_path(ip)}" for ip in ips]
    comandos += [f"  add_files -fileset sim_1 {tcl_path(f)}" for f in fontes]
    comandos += [
        "  set_property file_type {VHDL 2008} [get_files -of_objects [get_filesets sim_1] -filter {FILE_TYPE == VHDL}]",
        "}",
        "set_property top tb_todas [get_filesets sim_1]",
        f"set_property generic [list RAIZ={tcl_path(RAIZ)}] [get_filesets sim_1]",
        "set_property xsim.simulate.runtime all [get_filesets sim_1]",
        "update_compile_order -fileset sim_1",
        "launch_simulation -simset sim_1 -mode behavioral",
        "close_sim",
        "close_project",
    ]
    # Um elemento Tcl contendo NAME=value deve ser criado como uma unica string.
    comandos = [c.replace(f"[list RAIZ={tcl_path(RAIZ)}]",
                         f'[list "RAIZ={RAIZ.as_posix()}"]') for c in comandos]
    script.write_text("\n".join(comandos) + "\n", encoding="utf-8")
    return metas, quantidade, script


def ler_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def salvar_csv(path, linhas):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader(); w.writerows(linhas)


def resumir(metas, quantidade):
    resumo = []
    for meta in metas:
        nome = meta["nome"]
        pasta = RAIZ / nome / "testbench"
        arquivo = pasta / f"{nome}_output.csv"
        linhas = ler_csv(arquivo)
        fluxo = ler_csv(pasta / f"{nome}_fluxo.csv")
        if len(linhas) != quantidade or len(fluxo) != quantidade:
            raise RuntimeError(f"{nome}: simulacao incompleta")
        for l in linhas:
            # Hex e a representacao exata; real'image varia entre simuladores.
            def numero(h):
                bits = int(h, 16)
                if meta["inteiro"]:
                    return bits - (1 << 32) if bits >> 31 else bits
                return struct.unpack(">f", bytes.fromhex(h))[0]
            for coluna, hexadecimal in (("valor_entrada_a", "a_hex"),
                                        ("valor_entrada_b", "b_hex"),
                                        ("valor_entrada_c", "c_hex"),
                                        ("valor_saida", "saida_hex"),
                                        ("valor_esperado", "esperado_hex")):
                try:
                    l[coluna] = str(numero(l[hexadecimal]))
                except ValueError:
                    l[coluna] = "INDEFINIDO"
            if l["valor_saida"] != "INDEFINIDO":
                obtido, esperado = float(l["valor_saida"]), float(l["valor_esperado"])
                l["erro_absoluto_referencia"] = abs(obtido - esperado)
                if meta["inteiro"]:
                    l["erro_ulp"] = "N/A"
                else:
                    def ordem(h):
                        x = int(h, 16)
                        return 0x80000000 - (x & 0x7FFFFFFF) if x >> 31 else 0x80000000 + x
                    l["erro_ulp"] = abs(ordem(l["saida_hex"]) - ordem(l["esperado_hex"]))
                exato = int(float(l["valor_entrada_a"])) * int(float(l["valor_entrada_b"])) + int(float(l["valor_entrada_c"]))
                l["erro_absoluto_matematico"] = abs(obtido-exato)
            else:
                l.update(erro_absoluto_referencia="N/A", erro_ulp="N/A", erro_absoluto_matematico="N/A")
            l["simulacao"] = "RTL_com_IP_Xilinx_Vivado"
        salvar_csv(arquivo, linhas)
        resumo.append(dict(
            nome_arquitetura=nome, testes=quantidade,
            falhas=sum(l["status"] != "PASS" for l in linhas),
            falhas_fluxo=sum(l["status"] != "PASS" for l in fluxo),
            latencia_ciclos=meta["latencia"], intervalo_iniciacao_ciclos=meta["intervalo"],
            periodo_teste_ns=10,
            latencia_nominal_teste_ns=meta["latencia"]*10,
            vazao_teste_Mops_s=100/meta["intervalo"] if meta["tem_clock"] else "N/A",
            max_valores_intermediarios=max(int(l["valores_intermediarios_observados"]) for l in linhas),
            max_erro_absoluto_matematico=max((float(l["erro_absoluto_matematico"]) for l in linhas if l["erro_absoluto_matematico"] != "N/A"), default="N/A"),
            simulacao="RTL_com_IP_Xilinx_Vivado"))
    salvar_csv(RAIZ / "testbench/resumo_arquiteturas.csv", resumo)
    for r in resumo:
        print(f'{r["nome_arquitetura"]:30} lat={r["latencia_ciclos"]:2} '
              f'II={r["intervalo_iniciacao_ciclos"]:2} falhas={r["falhas"]} fluxo={r["falhas_fluxo"]}')
    return not any(r["falhas"] or r["falhas_fluxo"] for r in resumo)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arquiteturas", nargs="+", choices=ARQUITETURAS, default=list(ARQUITETURAS))
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--preparar", action="store_true", help="Somente gera vetores, adaptadores e Tcl")
    modo.add_argument("--resumir", action="store_true", help="Processa os CSVs existentes, sem simular nem regenerar entradas")
    parser.add_argument("--vivado", help="Caminho do vivado ou vivado.bat")
    args = parser.parse_args()
    if args.resumir:
        quantidade = len((RAIZ / "testbench/vetores.txt").read_text(encoding="ascii").splitlines())
        return 0 if resumir([metadados(n) for n in args.arquiteturas], quantidade) else 1
    metas, quantidade, script = preparar(args.arquiteturas)
    print(f"{quantidade} entradas comuns. Tcl: {script}", flush=True)
    if args.preparar:
        return 0
    vivado = args.vivado or shutil.which("vivado")
    if not vivado:
        candidatos = [Path("D:/Xilinx/2025.1/Vivado/bin/vivado.bat"),
                      Path("C:/AMDDesignTools/2025.1/Vivado/bin/vivado.bat")]
        vivado = next((str(p) for p in candidatos if p.is_file()), None)
    if not vivado:
        parser.error("Vivado nao encontrado; informe --vivado. Nenhum resultado foi fabricado.")
    for arquivo in ("resumo_arquiteturas.csv", "ultima_execucao.json"):
        (RAIZ / "testbench" / arquivo).unlink(missing_ok=True)
    # Remove apenas CSVs de saida anteriores desta execucao para impedir uso de dados antigos.
    for m in metas:
        for sufixo in ("output", "fluxo"):
            (RAIZ / m["nome"] / "testbench" / f'{m["nome"]}_{sufixo}.csv').unlink(missing_ok=True)
    log = script.parent / "vivado.log"
    with (script.parent / "console.log").open("w", encoding="utf-8") as console:
        resultado = subprocess.run([vivado, "-mode", "batch", "-source", str(script),
                                    "-log", str(log), "-nojournal"],
                                   cwd=script.parent, stdout=console, stderr=subprocess.STDOUT)
    if resultado.returncode:
        print(f"Vivado falhou. Consulte {log}", file=sys.stderr)
        return resultado.returncode
    ok = resumir(metas, quantidade)
    (RAIZ / "testbench/ultima_execucao.json").write_text(json.dumps(
        dict(vetores=quantidade, arquiteturas=args.arquiteturas, log=str(log),
             sha256_vetores=hashlib.sha256((RAIZ / 'testbench/vetores.txt').read_bytes()).hexdigest(),
             sucesso=ok), indent=2), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
