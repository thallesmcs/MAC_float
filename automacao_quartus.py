import os
import re
import csv  # <--- 1. Adicionei esta biblioteca

# ================= CONFIGURAÇÃO =================
# Ponto de partida da busca ('.' significa a pasta onde o script está)
DIRETORIO_RAIZ = "." 
NOME_CSV = "relatorio_final.csv" # <--- 2. Nome do arquivo de saída
CLOCK_ALVO = "ap_clk"
# ================================================

def extrair_fmax(content):
    """Seleciona somente ap_clk, no menor Fmax dos modelos Slow a 85 C.

    Ignora o indice do relatorio, outros clocks e outras tabelas de timing.
    O Restricted Fmax e mantido separado do Fmax, como no TimeQuest.
    """
    candidatos = []
    modelo = None
    cabecalho = False
    for line in content.splitlines():
        titulo = line.strip().strip(";").strip()
        if re.fullmatch(r"Slow\s+.+?\s+85C\s+Model Fmax Summary", titulo):
            modelo, cabecalho = titulo, False
            continue
        if "Summary" in titulo or (not titulo and cabecalho):
            modelo, cabecalho = None, False
        if not modelo:
            continue
        campos = [c.strip() for c in line.strip().strip(";").split(";")]
        if len(campos) >= 3 and campos[:3] == ["Fmax", "Restricted Fmax", "Clock Name"]:
            cabecalho = True
            continue
        if not cabecalho or len(campos) < 3 or campos[2] != CLOCK_ALVO:
            continue
        def mhz(texto):
            m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s+MHz", texto)
            return float(m[1]) if m else None
        fmax = mhz(campos[0])
        if fmax is not None:
            candidatos.append((fmax, mhz(campos[1]), modelo))
    return min(candidatos, key=lambda item: item[0]) if candidatos else None


def extrair_dados_quartus(caminho_pasta, nome_design):
    """
    Lê os arquivos .fit.summary e .sta.rpt para extrair os dados reais.
    """

    def _parse_int(valor):
        # Remove separadores de milhar como ',' ou '.' antes de converter
        if not valor:
            return None
        digitos = re.sub(r"[^0-9]", "", valor)
        return int(digitos) if digitos else None
    
    arquivo_fit = os.path.join(caminho_pasta, f"{nome_design}.fit.summary")
    arquivo_sta = os.path.join(caminho_pasta, f"{nome_design}.sta.rpt")
    try:
        pasta_relatorio = os.path.relpath(caminho_pasta)
    except ValueError:  # Windows: raiz de busca em outra unidade.
        pasta_relatorio = os.path.abspath(caminho_pasta)

    dados = {
        "design": nome_design,
        "pasta": pasta_relatorio, # Mostra onde achou
        "logic_util": "N/A",
        "registers": "N/A",
        "pins": "N/A",
        "dsp_blocks": "N/A",
        "embedded_mult_9bit": "N/A",
        "dsp_18bit": "N/A",
        "memory_bits": "N/A",
        "fmax": "N/A",
        "restricted_fmax": "N/A",
        "period_ns": "N/A",
        "timing_model": "N/A",
        "clock": CLOCK_ALVO,
        "status": "OK"
    }

    # 1. LER LEs REAIS (Fitter)
    if os.path.exists(arquivo_fit):
        try:
            with open(arquivo_fit, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            match_status = re.search(r"^Fitter Status\s*:\s*(.+)$", content, re.MULTILINE)
            if match_status and not match_status[1].strip().startswith("Successful"):
                dados["status"] = "FIT nao concluido"
            
            # Tenta pegar Logic Elements
            match = re.search(r"Total logic elements.*?:\s*([0-9,\.]+)\s*/", content)
            if match:
                valor = _parse_int(match.group(1))
                if valor is not None:
                    dados["logic_util"] = valor
            else:
                # Tenta pegar ALMs (para Cyclone V ou mais novos)
                match_alm = re.search(r"Logic utilization.*?:\s*([0-9,\.]+)\s*/", content)
                if match_alm:
                    valor = _parse_int(match_alm.group(1))
                    if valor is not None:
                        dados["logic_util"] = f"{valor} (ALMs)"

            match_regs = re.search(r"(?:Total registers|Dedicated logic registers)\s*:\s*([0-9,\.]+)", content)
            if match_regs:
                valor = _parse_int(match_regs.group(1))
                if valor is not None:
                    dados["registers"] = valor

            match_pins = re.search(r"Total pins\s*:\s*([0-9,\.]+)\s*/", content)
            if match_pins:
                valor = _parse_int(match_pins.group(1))
                if valor is not None:
                    dados["pins"] = valor

            match_dsp = re.search(r"^Total DSP Blocks\s*:\s*([0-9,\.]+)\s*/", content, re.MULTILINE | re.IGNORECASE)
            if match_dsp:
                valor = _parse_int(match_dsp.group(1))
                if valor is not None:
                    dados["dsp_blocks"] = valor
            # Cyclone IV informa multiplicadores de 9 bits, nao 'Total DSP Blocks'.
            # Mantem a unidade separada para nao comparar recursos diferentes.
            for chave, rotulo in (("embedded_mult_9bit", "Embedded Multiplier 9-bit elements"),
                                  ("dsp_18bit", "DSP block 18-bit elements"),
                                  ("memory_bits", "Total memory bits")):
                match = re.search(r"^" + re.escape(rotulo) + r"\s*:\s*([0-9,\.]+)", content,
                                  re.MULTILINE | re.IGNORECASE)
                if match:
                    dados[chave] = _parse_int(match[1])
        except Exception as e:
            dados["status"] = f"Erro leitura FIT"
    else:
        dados["status"] = "Sem FIT"

    # 2. LER FMAX REAL (Slow 85C)
    if os.path.exists(arquivo_sta):
        try:
            with open(arquivo_sta, 'r', encoding='utf-8', errors='ignore') as f:
                resultado = extrair_fmax(f.read())
            if resultado:
                dados["fmax"], restrito, dados["timing_model"] = resultado
                dados["restricted_fmax"] = restrito if restrito is not None else "N/A"
                dados["period_ns"] = round(1000 / dados["fmax"], 6) if dados["fmax"] > 0 else "N/A"
            else:
                dados["fmax"] = "Sem ap_clk/85C"

        except Exception as e:
            dados["status"] = f"Erro leitura STA"
    else:
         if dados["status"] == "OK": dados["status"] = "Sem STA"

    return dados

def main():
    print(f"--- Iniciando varredura RECURSIVA em: {os.path.abspath(DIRETORIO_RAIZ)} ---\n")
    
    resultados = []
    
    # os.walk percorre todas as pastas e subpastas
    for root, dirs, files in os.walk(DIRETORIO_RAIZ):
        dirs[:] = sorted(d for d in dirs if d.lower() not in {"codigos_c_hls", ".git", ".sim"})
        for file in files:
            # Identifica arquivos de relatório do Fitter
            if file.endswith(".fit.summary"):
                # O nome do design é o nome do arquivo sem a extensão
                nome_design = file.replace(".fit.summary", "")
                
                # Chama a função passando a pasta onde o arquivo foi encontrado
                resultado = extrair_dados_quartus(root, nome_design)
                resultados.append(resultado)

    if not resultados:
        print("Nenhum relatório (.fit.summary) encontrado nas subpastas.")
        return

    # --- CONFIGURAÇÃO DE LARGURAS ---
    # Definindo larguras fixas para garantir que Cabeçalho e Linhas batam exatamente
    W_DESIGN = 45
    W_LOGIC = 24
    W_REGS = 12
    W_PINS = 10
    W_DSP = 10
    W_FMAX = 12
    W_PASTA = 60  # Aumentei um pouco para caber caminhos melhores
    W_STATUS = 10 # Tamanho fixo para o status

    # --- IMPRIMIR CABEÇALHO ---
    # O segredo é usar o mesmo número (ex: :<30) no cabeçalho e no loop
    header = (
        f"{'DESIGN':<{W_DESIGN}} | "
        f"{'Total Logic Utilization':<{W_LOGIC}} | "
        f"{'Total Registers':<{W_REGS}} | "
        f"{'Total Pins':<{W_PINS}} | "
        f"{'DSP Blocks':<{W_DSP}} | "
        f"{'FMAX (85C)':<{W_FMAX}} | "
        f"{'MULT 9-bit':>10} | {'DSP 18-bit':>10} | {'MEM bits':>12} | {'FMAX restrito':>13} | "
        f"{'PASTA':<{W_PASTA}} | "
        f"{'STATUS':<{W_STATUS}}"
    )

    print(header)
    print("-" * len(header))

    # --- IMPRIMIR LINHAS ---
    for item in resultados:
        # 1. Tratar Design (Corta se passar da largura)
        design_str = item['design']
        if len(design_str) > W_DESIGN:
            design_str = design_str[:W_DESIGN-2] + '..'
        
        # 2. Tratar Pasta (Corta o INÍCIO se passar da largura, para ver o final da pasta)
        pasta_str = item['pasta']
        if len(pasta_str) > W_PASTA:
            # Pega os ultimos caracteres que cabem, deixando espaço para '...'
            pasta_str = '...' + pasta_str[-(W_PASTA-3):] 

        # 3. Status e Conversões
        logic_str = str(item['logic_util'])
        regs_str = str(item['registers'])
        pins_str = str(item['pins'])
        dsp_str = str(item['dsp_blocks'])
        fmax_str = str(item['fmax'])
        status_str = item['status']

        # 4. Print com as MESMAS larguras do cabeçalho
        print(
            f"{design_str:<{W_DESIGN}} | "
            f"{logic_str:<{W_LOGIC}} | "
            f"{regs_str:<{W_REGS}} | "
            f"{pins_str:<{W_PINS}} | "
            f"{dsp_str:<{W_DSP}} | "
            f"{fmax_str:<{W_FMAX}} | "
            f"{str(item['embedded_mult_9bit']):>10} | {str(item['dsp_18bit']):>10} | {str(item['memory_bits']):>12} | {str(item['restricted_fmax']):>13} | "
            f"{pasta_str:<{W_PASTA}} | "
            f"{status_str:<{W_STATUS}}" # Aqui garante que o OK fique alinhado com STATUS
        )

# --- 3. GERAR ARQUIVO CSV ---
    try:
        with open(NOME_CSV, mode='w', newline='', encoding='utf-8') as csv_file:
            # Definindo as colunas
            colunas = [
                'DESIGN',
                'Total Logic Utilization',
                'Total Registers',
                'Total Pins',
                'DSP Blocks',
                'FMAX (85C)',
                'Embedded Multiplier 9-bit elements',
                'DSP block 18-bit elements',
                'Total memory bits',
                'Restricted FMAX (85C)',
                'Periodo FMAX (ns)',
                'Clock',
                'Modelo timing',
                'PASTA',
                'STATUS'
            ]
            writer = csv.writer(csv_file)
            
            # Escreve o cabeçalho
            writer.writerow(colunas)
            
            # Escreve os dados (usando os dados originais, sem cortes '...')
            for item in resultados:
                writer.writerow([
                    item['design'], 
                    item['logic_util'], 
                    item['registers'],
                    item['pins'],
                    item['dsp_blocks'],
                    item['fmax'], 
                    item['embedded_mult_9bit'],
                    item['dsp_18bit'],
                    item['memory_bits'],
                    item['restricted_fmax'],
                    item['period_ns'],
                    item['clock'],
                    item['timing_model'],
                    item['pasta'], 
                    item['status']
                ])
        
        print(f"\n[SUCESSO] Arquivo CSV gerado: {os.path.abspath(NOME_CSV)}")
        
    except Exception as e:
        print(f"\n[ERRO] Não foi possível gerar o CSV: {e}")

if __name__ == "__main__":
    main()
