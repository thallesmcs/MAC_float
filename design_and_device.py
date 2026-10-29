import os
import re
import csv

# ================= CONFIGURAÇÃO =================
DIRETORIO_RAIZ = "." 
NOME_CSV = "relatorio_design_device.csv"
# ================================================

def extrair_placa(caminho_pasta, nome_design):
    """
    Lê apenas o .fit.summary para pegar o Device.
    """
    arquivo_fit = os.path.join(caminho_pasta, f"{nome_design}.fit.summary")
    
    device = "N/A"
    
    if os.path.exists(arquivo_fit):
        try:
            with open(arquivo_fit, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Procura a linha "Device : <MODELO>"
            # O regex pega o texto logo após os dois pontos até o primeiro espaço/quebra de linha
            match_dev = re.search(r"^\s*Device\s*:\s*([^\s]+)", content, re.MULTILINE)
            if match_dev:
                device = match_dev.group(1)
                
        except Exception:
            device = "Erro Leitura"
            
    return {"design": nome_design, "device": device}

def main():
    print(f"--- Buscando Designs e Placas em: {os.path.abspath(DIRETORIO_RAIZ)} ---\n")
    
    resultados = []
    
    # Varredura recursiva
    for root, dirs, files in os.walk(DIRETORIO_RAIZ):
        dirs[:] = sorted(d for d in dirs if d.lower() not in {"codigos_c_hls", ".git", ".sim"})
        for file in files:
            if file.endswith(".fit.summary"):
                nome_design = file.replace(".fit.summary", "")
                dados = extrair_placa(root, nome_design)
                resultados.append(dados)

    if not resultados:
        print("Nenhum projeto encontrado.")
        return

    # --- IMPRIMIR TABELA NO TERMINAL ---
    W_DESIGN = 45
    W_DEVICE = 25
    
    header = f"{'DESIGN':<{W_DESIGN}} | {'DEVICE (PLACA)':<{W_DEVICE}}"
    print(header)
    print("-" * len(header))

    for item in resultados:
        # Corta o nome se for muito longo para não quebrar a tabela visualmente
        d_str = (item['design'][:W_DESIGN-2] + '..') if len(item['design']) > W_DESIGN else item['design']
        print(f"{d_str:<{W_DESIGN}} | {item['device']:<{W_DEVICE}}")

    # --- GERAR CSV ---
    try:
        with open(NOME_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Cabeçalho do CSV
            writer.writerow(['DESIGN', 'DEVICE'])
            
            # Dados
            for item in resultados:
                writer.writerow([item['design'], item['device']])
        
        print(f"\n[SUCESSO] Arquivo gerado: {NOME_CSV}")
        
    except Exception as e:
        print(f"\n[ERRO] Ao salvar CSV: {e}")

if __name__ == "__main__":
    main()
