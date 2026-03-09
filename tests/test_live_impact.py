import unittest

from ncm_monitor.live_sites import _build_import_impact, _build_objective_impact


class LiveImpactTest(unittest.TestCase):
    def test_split_summary_for_ncm(self):
        text = """
        A NCM 6506.10.00 deixa de existir a partir de 01/02/2026.
        Passa a ser desdobrada em 6506.10.10 e 6506.10.90.
        Para 6506.10.90, pode haver licenciamento do Ministerio da Defesa
        em operacoes de importacao e exportacao.
        Nao houve mudanca automatica de aliquota de IPI.
        """
        resumo, acao, relacionadas = _build_objective_impact("65061000", "ALTERACAO", text)
        self.assertIn("6506.10.00", resumo)
        self.assertIn("6506.10.10", resumo)
        self.assertIn("6506.10.90", resumo)
        self.assertIn("Nao use mais", acao)
        self.assertIn("65061010", relacionadas)
        self.assertIn("65061090", relacionadas)

    def test_import_impact_for_split_and_licensing(self):
        text = """
        A NCM 6506.10.00 deixa de existir a partir de 01/02/2026.
        Passa a ser desdobrada em 6506.10.10 e 6506.10.90.
        Para 6506.10.90, pode haver licenciamento do Ministerio da Defesa na importacao.
        """
        impacto, acao = _build_import_impact(
            target_ncm="65061000",
            tipo="ALTERACAO",
            full_text=text,
            ncms_relacionadas=["65061010", "65061090"],
        )
        self.assertIn("deve migrar", impacto)
        self.assertIn("6506.10.10", impacto)
        self.assertIn("6506.10.90", impacto)
        self.assertIn("DI/DUIMP", acao)
        self.assertIn("licenciamento/anuencia", acao)


if __name__ == "__main__":
    unittest.main()
