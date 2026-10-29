"""Regressoes com trechos sinteticos no formato dos relatorios Quartus."""
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automacao_quartus import extrair_dados_quartus, extrair_fmax
from design_and_device import extrair_placa


def tabela(modelo, linhas):
    return (f"; {modelo} Model Fmax Summary ;\n"
            "; Fmax ; Restricted Fmax ; Clock Name ; Note ;\n" + linhas + "\n\n")


class RelatoriosTest(unittest.TestCase):
    def test_clock_exato_e_modelo(self):
        conteudo = "; 2.1 ; Slow 1100mV 85C Model Fmax Summary ;\n" + tabela(
            "Slow 1100mV 0C", "; 400.0 MHz ; 350.0 MHz ; ap_clk ;\n") + tabela(
            "Slow 1100mV 85C",
            "; 999.0 MHz ; 999.0 MHz ; clk ;\n"
            "; 888.0 MHz ; 888.0 MHz ; ap_clk_aux ;\n"
            "; 123.45 MHz ; 120.00 MHz ; ap_clk ;\n")
        self.assertEqual(extrair_fmax(conteudo), (123.45, 120.0, "Slow 1100mV 85C Model Fmax Summary"))

    def test_sem_clock_nao_pega_outra_tabela(self):
        conteudo = tabela("Slow 1100mV 85C", "; 999 MHz ; 999 MHz ; other_clk ;\n")
        conteudo += "; Setup Summary ;\n; 123 MHz ; 123 MHz ; ap_clk ;\n"
        self.assertIsNone(extrair_fmax(conteudo))

    def test_multiplos_modelos_slow_85(self):
        conteudo = tabela("Slow 1200mV 85C", "; 200 MHz ; 180 MHz ; ap_clk ;\n")
        conteudo += tabela("Slow 1100mV 85C", "; 150.5 MHz ; 140 MHz ; ap_clk ;\n")
        self.assertEqual(extrair_fmax(conteudo)[:2], (150.5, 140.0))

    def test_fit_device_e_unidades(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "mac_float.fit.summary").write_text(
                "Fitter Status : Successful - Thu Oct 29\n"
                "Family : Cyclone IV E\nTarget Device : errado\nDevice : EP4CE115F29C7\n"
                "Total logic elements : 1,234 / 114,480 (1 %)\n"
                "Total registers : 456\nTotal pins : 130 / 529\n"
                "Embedded Multiplier 9-bit elements : 14 / 532\n"
                "Total memory bits : 1,024 / 3,981,312\n", encoding="utf-8")
            (p / "mac_float.sta.rpt").write_text(tabela(
                "Slow 1200mV 85C", "; 125 MHz ; 120 MHz ; ap_clk ;\n"), encoding="utf-8")
            r = extrair_dados_quartus(tmp, "mac_float")
            self.assertEqual((r["logic_util"], r["registers"], r["embedded_mult_9bit"],
                              r["memory_bits"], r["period_ns"]), (1234, 456, 14, 1024, 8.0))
            self.assertEqual(r["dsp_blocks"], "N/A")
            self.assertEqual(extrair_placa(tmp, "mac_float")["device"], "EP4CE115F29C7")

    def test_nao_inventa_metricas_ausentes(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = extrair_dados_quartus(tmp, "mac_float")
            self.assertEqual(r["fmax"], "N/A")
            self.assertEqual(r["status"], "Sem FIT")


if __name__ == "__main__":
    unittest.main()
