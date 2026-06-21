"""Tests for the P2 RAG retrieval pipeline (chunk/embed/store/cite)."""

import unittest

from digikey_scraper.application.rag_service import ExtractiveAnswerer, RagService
from digikey_scraper.domain.rag import Answer, Chunk, RetrievedChunk
from digikey_scraper.infrastructure.rag.chunker import chunk_text
from digikey_scraper.infrastructure.rag.hashing_embedder import HashingEmbedder
from digikey_scraper.infrastructure.rag.memory_vector_store import InMemoryVectorStore

DATASHEET = (
    "The LM358 is a dual operational amplifier. "
    "Supply voltage range is 3V to 32V single supply. "
    "The operating temperature range is 0C to 70C. "
    "Input offset voltage is 2mV typical. "
    "The package is an 8-pin PDIP through-hole device."
)


class ChunkerTests(unittest.TestCase):
    def test_chunks_cover_text_with_overlap(self):
        chunks = chunk_text(DATASHEET, "lm358", max_chars=60, overlap=10)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(c.id.startswith("lm358:") for c in chunks))
        self.assertTrue(all(len(c.text) <= 60 for c in chunks))

    def test_empty_text_yields_no_chunks(self):
        self.assertEqual(chunk_text("   ", "d"), [])

    def test_invalid_params_rejected(self):
        with self.assertRaises(ValueError):
            chunk_text("x", "d", max_chars=0)
        with self.assertRaises(ValueError):
            chunk_text("x", "d", max_chars=10, overlap=10)


class EmbedderTests(unittest.TestCase):
    def test_deterministic_and_normalized(self):
        emb = HashingEmbedder(dim=64)
        a = emb.embed(["supply voltage range"])[0]
        b = emb.embed(["supply voltage range"])[0]
        self.assertEqual(a, b)  # deterministic
        norm = sum(x * x for x in a) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=6)
        self.assertEqual(emb.dim, 64)

    def test_similar_text_more_similar(self):
        emb = HashingEmbedder(dim=512)

        def dot(x, y):
            return sum(a * b for a, b in zip(x, y, strict=False))

        q = emb.embed(["operating temperature range"])[0]
        close = emb.embed(["the operating temperature range is wide"])[0]
        far = emb.embed(["pin package through hole"])[0]
        self.assertGreater(dot(q, close), dot(q, far))


class VectorStoreTests(unittest.TestCase):
    def test_add_search_upsert(self):
        s = InMemoryVectorStore()
        s.add(["a", "b"], [[1.0, 0.0], [0.0, 1.0]], [{"t": "a"}, {"t": "b"}])
        res = s.search([1.0, 0.0], top_k=1)
        self.assertEqual(res[0][0], "a")
        # upsert same id
        s.add(["a"], [[0.0, 1.0]], [{"t": "a2"}])
        self.assertEqual(s.ids(), {"a", "b"})
        self.assertEqual(s.search([0.0, 1.0], top_k=1)[0][2]["t"] in ("a2", "b"), True)

    def test_length_mismatch_rejected(self):
        s = InMemoryVectorStore()
        with self.assertRaises(ValueError):
            s.add(["a"], [], [{}])


class ExtractiveAnswererTests(unittest.TestCase):
    def test_cites_used_chunks(self):
        retrieved = [
            RetrievedChunk(Chunk("d:0", "d", "supply voltage 3V to 32V"), 0.9),
            RetrievedChunk(Chunk("d:1", "d", "temperature 0C to 70C"), 0.4),
        ]
        ans = ExtractiveAnswerer(max_chunks=2).answer("voltage?", retrieved)
        self.assertEqual(ans.citations, ["d:0", "d:1"])
        self.assertIn("[d:0]", ans.text)

    def test_no_positive_score_returns_no_info(self):
        retrieved = [RetrievedChunk(Chunk("d:0", "d", "x"), 0.0)]
        ans = ExtractiveAnswerer().answer("q", retrieved)
        self.assertEqual(ans.citations, [])
        self.assertIn("No relevant", ans.text)


class RagServiceTests(unittest.TestCase):
    def _service(self):
        return RagService(HashingEmbedder(dim=512), InMemoryVectorStore(), max_chars=60, overlap=10)

    def test_index_then_query_returns_relevant_cited_answer(self):
        svc = self._service()
        n = svc.index("lm358", DATASHEET)
        self.assertGreater(n, 0)
        ans = svc.query("what is the supply voltage range?", top_k=2)
        self.assertTrue(ans.citations)  # has citations
        self.assertIn("voltage", ans.text.lower())
        # every citation references a real indexed chunk
        self.assertTrue(set(ans.citations) <= svc.store.ids())

    def test_citations_grounded_in_retrieved(self):
        # answerer that fabricates a bogus citation -> guard must drop it
        class BadAnswerer:
            def answer(self, question, retrieved):
                cites = [r.chunk.id for r in retrieved] + ["FAKE:999"]
                return Answer(text="x", citations=cites, retrieved=retrieved)

        svc = RagService(
            HashingEmbedder(dim=256),
            InMemoryVectorStore(),
            answerer=BadAnswerer(),
            max_chars=60,
            overlap=10,
        )
        svc.index("d", DATASHEET)
        ans = svc.query("voltage", top_k=2)
        self.assertNotIn("FAKE:999", ans.citations)
        self.assertTrue(set(ans.citations) <= svc.store.ids())

    def test_empty_document_indexes_nothing(self):
        svc = self._service()
        self.assertEqual(svc.index("d", "   "), 0)


if __name__ == "__main__":
    unittest.main()
