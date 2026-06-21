"""Tests for P2 LLM answerer + citation-enforcing cross-verification."""

import unittest

from digikey_scraper.application.answerers import (
    CitationEnforcingAnswerer,
    LLMAnswerer,
    groundedness,
)
from digikey_scraper.application.rag_service import RagService
from digikey_scraper.domain.rag import Answer, Chunk, RetrievedChunk
from digikey_scraper.infrastructure.rag.hashing_embedder import HashingEmbedder
from digikey_scraper.infrastructure.rag.memory_vector_store import InMemoryVectorStore


class FakeGenerator:
    def __init__(self, output):
        self.output = output
        self.last_prompt = None

    def generate(self, prompt):
        self.last_prompt = prompt
        return self.output


def _retrieved():
    return [
        RetrievedChunk(Chunk("d:0", "d", "Supply voltage is 3V to 32V single supply."), 0.9),
        RetrievedChunk(Chunk("d:1", "d", "Operating temperature is 0C to 70C."), 0.5),
    ]


class GroundednessTests(unittest.TestCase):
    def test_full_and_partial(self):
        self.assertEqual(groundedness("3V to 32V", "supply voltage is 3v to 32v"), 1.0)
        self.assertLess(groundedness("5V to 99V xyz", "supply voltage is 3v to 32v"), 1.0)

    def test_empty_answer_is_grounded(self):
        self.assertEqual(groundedness("", "anything"), 1.0)


class LLMAnswererTests(unittest.TestCase):
    def test_parses_citation_markers(self):
        gen = FakeGenerator("Supply voltage is 3V to 32V [1].")
        ans = LLMAnswerer(gen).answer("voltage?", _retrieved())
        self.assertEqual(ans.citations, ["d:0"])
        self.assertIn("Context:", gen.last_prompt)  # prompt was built
        self.assertIn("[1]", gen.last_prompt)  # chunks numbered for citation

    def test_multiple_unique_citations(self):
        gen = FakeGenerator("Voltage [1] and temperature [2] and again [1].")
        ans = LLMAnswerer(gen).answer("specs?", _retrieved())
        self.assertEqual(ans.citations, ["d:0", "d:1"])

    def test_out_of_range_marker_ignored(self):
        gen = FakeGenerator("Bogus [9].")
        ans = LLMAnswerer(gen).answer("q", _retrieved())
        self.assertEqual(ans.citations, [])

    def test_no_positive_score_short_circuits(self):
        gen = FakeGenerator("should not be called")
        ans = LLMAnswerer(gen).answer("q", [RetrievedChunk(Chunk("d:0", "d", "x"), 0.0)])
        self.assertIn("No relevant", ans.text)
        self.assertIsNone(gen.last_prompt)  # generator not invoked


class FixedAnswerer:
    def __init__(self, answer):
        self._answer = answer

    def answer(self, question, retrieved):
        return self._answer


class CitationEnforcingTests(unittest.TestCase):
    def test_grounded_answer_passes(self):
        inner = FixedAnswerer(
            Answer(text="Supply voltage is 3V to 32V single supply.", citations=["d:0"])
        )
        out = CitationEnforcingAnswerer(inner).answer("v?", _retrieved())
        self.assertEqual(out.citations, ["d:0"])

    def test_fabricated_citation_dropped(self):
        inner = FixedAnswerer(Answer(text="3V to 32V", citations=["d:0", "FAKE"]))
        out = CitationEnforcingAnswerer(inner).answer("v?", _retrieved())
        self.assertEqual(out.citations, ["d:0"])

    def test_unsupported_answer_rejected(self):
        # cites a real chunk but states content not in it -> low groundedness
        inner = FixedAnswerer(
            Answer(
                text="The device supports wireless bluetooth mesh networking protocol",
                citations=["d:0"],
            )
        )
        out = CitationEnforcingAnswerer(inner, min_groundedness=0.5).answer("v?", _retrieved())
        self.assertEqual(out.citations, [])
        self.assertIn("not sufficiently supported", out.text)

    def test_no_valid_citations_refuses(self):
        inner = FixedAnswerer(Answer(text="anything", citations=["FAKE"]))
        out = CitationEnforcingAnswerer(inner).answer("q", _retrieved())
        self.assertIn("Insufficient grounded", out.text)


class IntegrationTests(unittest.TestCase):
    def test_rag_service_with_enforced_llm_answerer(self):
        datasheet = "Supply voltage is 3V to 32V single supply. Temperature 0C to 70C."
        # honest model: echoes grounded text with a citation
        gen = FakeGenerator("Supply voltage is 3V to 32V single supply [1].")
        answerer = CitationEnforcingAnswerer(LLMAnswerer(gen))
        svc = RagService(
            HashingEmbedder(dim=512),
            InMemoryVectorStore(),
            answerer=answerer,
            max_chars=80,
            overlap=10,
        )
        svc.index("d", datasheet)
        ans = svc.query("what is the supply voltage?", top_k=2)
        self.assertTrue(ans.citations)
        self.assertTrue(set(ans.citations) <= svc.store.ids())


if __name__ == "__main__":
    unittest.main()
