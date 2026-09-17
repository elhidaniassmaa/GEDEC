import unittest
from unittest.mock import patch

from src.argumentaire import reglementation

class TestFallbackLexical(unittest.TestCase):
    def setUp(self):
        self.clauses = [
            {"numero_article": "A1", "numero_tiret": "1", "texte_clause": "alpha beta gamma"},
            {"numero_article": "A1", "numero_tiret": "2", "texte_clause": "delta epsilon"},
            {"numero_article": "A2", "numero_tiret": "1", "texte_clause": "zeta eta theta"},
            {"numero_article": "A2", "numero_tiret": "2", "texte_clause": "iota kappa"},
            {"numero_article": "A3", "numero_tiret": "1", "texte_clause": "lambda mu nu"},
        ]
        self.request_text = "alpha beta"

    @patch.object(reglementation, "_get_embedder", return_value=None)
    @patch.object(reglementation, "get_clauses", return_value=None)
    def test_fallback_returns_top_k_intermediaire(self, mock_get_clauses, mock_embedder):
        mock_get_clauses.return_value = self.clauses
        result = reglementation.get_best_clause(
            code_direction="A1",
            texte_demande=self.request_text,
            top_k_intermediaire=3,
            verbose=False,
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["texte_clause"], self.clauses[0]["texte_clause"])
        self.assertEqual(result[1]["texte_clause"], self.clauses[1]["texte_clause"])
        self.assertIn(result[2]["texte_clause"], [c["texte_clause"] for c in self.clauses[2:]])

if __name__ == "__main__":
    unittest.main()
