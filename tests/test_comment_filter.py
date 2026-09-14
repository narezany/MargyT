"""Behavioural contract for the narrow verified-comment filter.

The production implementation is Android Java, so these dependency-free tests
exercise the rule semantics shared by its JSON format: verification is required,
allowlists win, and names are compared after NFKC/trim/case-fold/space folding.
"""
import re
import unicodedata
import unittest


def normalise(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip().casefold())


def should_hide(verified, name, uid, names, allow_names=(), allow_uids=(), patterns=()):
    name = normalise(name)
    return (verified and uid not in allow_uids and name not in set(map(normalise, allow_names))
            and (name in set(map(normalise, names))
                 or any(re.fullmatch(pattern, name) for pattern in patterns)))


class CommentFilterRulesTest(unittest.TestCase):
    def test_verified_exact_match_is_hidden(self):
        self.assertTrue(should_hide(True, "Impostor Studio", "42", ["impostor studio"]))

    def test_unverified_exact_match_is_not_hidden(self):
        self.assertFalse(should_hide(False, "Impostor Studio", "42", ["impostor studio"]))

    def test_official_allowlist_account_is_not_hidden(self):
        self.assertFalse(should_hide(True, "Impostor Studio", "official-42",
                                     ["impostor studio"], allow_uids=["official-42"]))

    def test_unicode_variants_normalise_before_exact_match(self):
        self.assertTrue(should_hide(True, "  Ｉｍｐｏｓｔｏｒ\u00a0\u00a0Ｓｔｕｄｉｏ  ", "42",
                                    ["impostor studio"]))

    def test_patterns_are_full_name_rules_not_word_matches(self):
        self.assertTrue(should_hide(True, "brand support 123", "42", [],
                                    patterns=[r"^brand support [0-9]{3}$"]))
        self.assertFalse(should_hide(True, "unrelated brand support 123 fan", "42", [],
                                     patterns=[r"^brand support [0-9]{3}$"]))


if __name__ == "__main__":
    unittest.main()
