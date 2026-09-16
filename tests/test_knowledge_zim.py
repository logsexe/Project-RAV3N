from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from fieldos.knowledge import KnowledgeEntry, KnowledgeIndex

# python-libzim (PyPI: `libzim`) is an optional extra (pyproject.toml's
# `library` extra, folded into `all-python`) -- a compiled, GPL-3.0-licensed
# binding around the openZIM C++ library. Every test below that needs the
# real package (to exercise the actual Archive/Searcher/Query API against a
# real .zim file) is skipped when it isn't installed; the "not installed"
# tests below always run, mocking importlib.util.find_spec the same way
# tests/test_live_services.py does for meshtastic, so fail-closed behaviour
# is verified regardless of what happens to be installed on the box running
# the suite.
LIBZIM_INSTALLED = importlib.util.find_spec("libzim") is not None

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample.zim"


def _open_fixture_archive():
    from libzim.reader import Archive

    return Archive(str(FIXTURE))


class _CountingArchiveProxy:
    """Wraps a real libzim Archive to count get_entry_by_path() calls.

    libzim's Archive is a Cython extension type with read-only attributes,
    so it can't be patched in place with unittest.mock.patch.object(); this
    plain-Python duck-typed wrapper is swapped into KnowledgeIndex's
    archive dict instead, after any Searcher-based lookups (which do
    require a real Archive instance) have already happened.
    """

    def __init__(self, real) -> None:
        self._real = real
        self.get_entry_by_path_calls = 0

    def get_entry_by_path(self, path: str):
        self.get_entry_by_path_calls += 1
        return self._real.get_entry_by_path(path)

    def __getattr__(self, name: str):
        return getattr(self._real, name)


class LibzimNotInstalledTests(unittest.TestCase):
    """LIBRARY must behave exactly as it does today when libzim is absent:
    zero ZIM entries, no crash, no exception surfaced anywhere."""

    def test_open_zim_archives_returns_empty_when_libzim_missing(self) -> None:
        with patch("fieldos.knowledge.importlib.util.find_spec", return_value=None):
            self.assertEqual(KnowledgeIndex._open_zim_archives(), {})

    def test_load_default_has_zero_zim_archives_when_libzim_missing(self) -> None:
        with patch("fieldos.knowledge.importlib.util.find_spec", return_value=None):
            index = KnowledgeIndex.load_default()
        self.assertEqual(index.zim_archive_count, 0)

    def test_search_zim_returns_empty_when_libzim_missing(self) -> None:
        # Even if archives were somehow already open, _search_zim must still
        # fail closed if libzim later reports as unavailable.
        index = KnowledgeIndex([], {"fake.zim": object()})
        with patch("fieldos.knowledge.importlib.util.find_spec", return_value=None):
            self.assertEqual(index._search_zim("anything", limit=10), [])

    def test_search_with_no_archives_returns_local_results_only(self) -> None:
        local = KnowledgeEntry(id="local:1", title="Tourniquet Basics", category="medical", body="apply pressure")
        index = KnowledgeIndex([local], {})
        results = index.search("tourniquet")
        self.assertEqual(results, [local])

    def test_body_for_local_entry_is_unaffected(self) -> None:
        local = KnowledgeEntry(id="local:1", title="Note", category="general", body="already loaded")
        index = KnowledgeIndex([local], {})
        self.assertEqual(index.body_for(local), "already loaded")


@unittest.skipUnless(LIBZIM_INSTALLED, "libzim is not installed in this environment")
class ZimFixtureSearchTests(unittest.TestCase):
    """Exercises the real libzim API (Archive/Searcher/Query) against a tiny
    real .zim fixture (tests/fixtures/sample.zim, 3 articles + 1 redirect,
    full-text indexed) rather than a hand-rolled mock of Xapian's ranking."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.archive = _open_fixture_archive()

    def _index(self) -> KnowledgeIndex:
        return KnowledgeIndex([], {str(FIXTURE): self.archive})

    def test_full_text_search_finds_article_by_body_content(self) -> None:
        # "rewarming" only appears in the hypothermia article's body, not its
        # title or our synthetic summary -- a hit here proves this is a real
        # full-text search over article content, not a title/summary substring
        # match against the (empty, lazily-loaded) KnowledgeEntry.body field.
        index = self._index()
        results = index.search("rewarming")
        self.assertTrue(any(r.zim_entry_path == "hypothermia" for r in results))

    def test_search_result_carries_lightweight_metadata_only(self) -> None:
        index = self._index()
        results = index.search("tourniquet bleeding")
        self.assertEqual(len(results), 1)
        entry = results[0]
        self.assertEqual(entry.title, "Applying a Tourniquet")
        self.assertEqual(entry.zim_source, str(FIXTURE))
        self.assertEqual(entry.zim_entry_path, "tourniquet")
        self.assertTrue(entry.is_zim)
        # The body must NOT have been fetched just because the entry matched.
        self.assertEqual(entry.body, "")

    def test_lazy_body_loading_fetches_only_on_access(self) -> None:
        index = self._index()
        entry = index.search("tourniquet bleeding")[0]
        self.assertEqual(entry.body, "", "body must stay empty until body_for() is called")

        # Swap the real archive for a call-counting proxy *after* the search
        # above (Searcher() requires a genuine libzim Archive instance) to
        # verify body_for() only reads the archive once, then serves its own
        # cache on every subsequent call for the same entry.
        proxy = _CountingArchiveProxy(self.archive)
        index._zim_archives[str(FIXTURE)] = proxy

        body = index.body_for(entry)
        self.assertEqual(proxy.get_entry_by_path_calls, 1)
        self.assertIn("tourniquet", body.lower())
        self.assertIn("bleeding", body.lower())

        body_again = index.body_for(entry)
        self.assertEqual(proxy.get_entry_by_path_calls, 1, "second access must hit KnowledgeIndex's cache")
        self.assertEqual(body_again, body)

    def test_body_is_stripped_of_html_markup(self) -> None:
        index = self._index()
        entry = index.search("tourniquet bleeding")[0]
        body = index.body_for(entry)
        self.assertNotIn("<", body)
        self.assertNotIn(">", body)
        self.assertIn("Applying a Tourniquet", body)

    def test_body_for_follows_redirect_entries(self) -> None:
        # "frostbite" is a pure redirect (add_redirection, no content of its
        # own) to the "hypothermia" article. A pure redirect carries no
        # indexable body text, so Xapian's full-text Searcher legitimately
        # never surfaces it for a body-content query -- but if any code path
        # (a future suggestion-search integration, or a hand-built
        # KnowledgeEntry) ever hands body_for() a redirect's own path, it
        # must still resolve through to the target article's real content
        # rather than returning empty or raising.
        index = self._index()
        redirect_entry = KnowledgeEntry(
            id="zim:test:frostbite", title="Frostbite (see Hypothermia)", category="reference",
            zim_source=str(FIXTURE), zim_entry_path="frostbite",
        )
        body = index.body_for(redirect_entry)
        self.assertIn("hypothermia", body.lower())
        self.assertIn("rewarming", body.lower())

    def test_empty_query_does_not_search_zim_archives(self) -> None:
        index = self._index()
        results = index.search("")
        self.assertFalse(any(r.is_zim for r in results))

    def test_category_is_guessed_from_archive_filename(self) -> None:
        with patch("fieldos.knowledge.zim_files", return_value=(FIXTURE,)):
            index = KnowledgeIndex.load_default()
        # "sample.zim" doesn't match any of the known category keywords, so
        # it must fall back to "reference" (the GENERAL section) rather than
        # being dropped or raising.
        results = index.search("tourniquet")
        self.assertTrue(results)
        self.assertEqual(results[0].category, "reference")

    def test_local_and_zim_results_merge_in_one_search_call(self) -> None:
        local = KnowledgeEntry(
            id="local:1", title="Tourniquet Field Notes", category="medical",
            summary="quick reference", body="tourniquet application quick reference card",
        )
        index = KnowledgeIndex([local], {str(FIXTURE): self.archive})
        results = index.search("tourniquet")
        sources = {r.source for r in results}
        self.assertIn("FIELD//OS", sources)  # the local entry's default source
        self.assertTrue(any(r.is_zim for r in results))


@unittest.skipUnless(LIBZIM_INSTALLED, "libzim is not installed in this environment")
class ZimArchiveDiscoveryFailureModesTests(unittest.TestCase):
    """Corrupt/missing files and broken archives must be skipped individually
    rather than taking down the whole knowledge index."""

    def test_unreadable_zim_file_is_skipped_not_raised(self) -> None:
        bogus = FIXTURE.parent / "not_actually_a_zim.zim"
        bogus.write_bytes(b"not a real zim file")
        try:
            with patch("fieldos.knowledge.zim_files", return_value=(bogus,)):
                archives = KnowledgeIndex._open_zim_archives()
            self.assertEqual(archives, {})
        finally:
            bogus.unlink()

    def test_one_bad_archive_does_not_block_a_good_one(self) -> None:
        bogus = FIXTURE.parent / "not_actually_a_zim2.zim"
        bogus.write_bytes(b"still not a real zim file")
        try:
            with patch("fieldos.knowledge.zim_files", return_value=(bogus, FIXTURE)):
                archives = KnowledgeIndex._open_zim_archives()
            self.assertEqual(set(archives.keys()), {str(FIXTURE)})
        finally:
            bogus.unlink()

    def test_searcher_exception_for_one_archive_does_not_block_others(self) -> None:
        good_archive = _open_fixture_archive()
        index = KnowledgeIndex([], {"broken.zim": object(), str(FIXTURE): good_archive})
        # "broken.zim" maps to a plain object() that libzim's real Searcher
        # cannot construct from -- _search_zim must swallow that per-archive
        # failure and still return the good archive's hits.
        results = index.search("tourniquet bleeding")
        self.assertTrue(any(r.zim_source == str(FIXTURE) for r in results))


if __name__ == "__main__":
    unittest.main()
