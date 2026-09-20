"""Test de vérification et intégration du rattachement SQLite <-> JSON RAG."""
import unittest
import os
import sys

# Assurer les chemins d'importation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.sync_base_reglementaire import (
    rattacher_articles_heritage,
    _charger_json,
    modifier_article_rag,
    supprimer_article_rag
)
from backend.database import get_db_connection, init_db


class TestSyncRag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_sync_rag_structure(self):
        """Vérifie que la table articles et le fichier JSON sont accessibles."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM articles")
        total_sqlite = cur.fetchone()[0]
        conn.close()

        self.assertGreaterEqual(total_sqlite, 0)

        data = _charger_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_rattacher_articles_heritage(self):
        """Vérifie que la fonction de rattachement s'exécute sans erreur."""
        result = rattacher_articles_heritage()
        self.assertIsInstance(result, int)


if __name__ == "__main__":
    unittest.main()
