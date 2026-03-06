import unittest

from ncm_monitor.dou import _extract_atos, _extract_total_pages, _extract_total_resultados


HTML_SAMPLE = """
<html><body>
<p class="search-total-label">127 resultados para <strong>ICMS</strong></p>
<script>
var request = { totalPages : 4, currentPage : 1 }
</script>
<script id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params" type="application/json">
{"jsonArray":[{"urlTitle":"ato-1","title":"Ato 1","classPK":"123","score":0.1,"displayDateSortable":"111"}]}
</script>
</body></html>
"""


class DOUParsingTest(unittest.TestCase):
    def test_total_resultados(self):
        self.assertEqual(_extract_total_resultados(HTML_SAMPLE), 127)

    def test_total_pages(self):
        self.assertEqual(_extract_total_pages(HTML_SAMPLE), 4)

    def test_extract_atos(self):
        atos = _extract_atos(HTML_SAMPLE)
        self.assertEqual(len(atos), 1)
        self.assertEqual(atos[0]["urlTitle"], "ato-1")


if __name__ == "__main__":
    unittest.main()

