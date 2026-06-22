"""test_export_helpers.py — pure-function tests for export.py helpers.

Covers:
- _slug: ASCII normalisation, lowercase, spaces → underscores
- _lua: dict/list/str/bool/int/float/None serialisation, string escaping
- _numeric_or_str: grade coercion, 0-9 only int-cast, comma decimal
"""
from __future__ import annotations

import pytest

from export import _slug, _lua, _numeric_or_str


# ---------------------------------------------------------------------------
# _slug
# ---------------------------------------------------------------------------

class TestSlug:
    def test_lowercase(self):
        assert _slug("Hello") == "hello"

    def test_spaces_become_underscores(self):
        assert _slug("Max Mustermann") == "max_mustermann"

    def test_umlaut_stripped(self):
        assert _slug("Müller") == "muller"

    def test_sz_stripped(self):
        assert _slug("Straße") == "strae"  # ß has no ASCII equivalent, drops

    def test_digits_preserved(self):
        assert _slug("7a") == "7a"

    def test_special_chars_removed(self):
        result = _slug("a!@#b")
        assert result == "ab"

    def test_leading_trailing_spaces(self):
        assert _slug("  foo  ") == "foo"

    def test_multiple_spaces_become_single_underscore(self):
        assert _slug("foo  bar") == "foo_bar"


# ---------------------------------------------------------------------------
# _lua – primitives
# ---------------------------------------------------------------------------

class TestLuaPrimitives:
    def test_string_simple(self):
        assert _lua("hello") == "'hello'"

    def test_string_empty(self):
        assert _lua("") == "''"

    def test_int(self):
        assert _lua(42) == "42"

    def test_float(self):
        assert _lua(3.14) == "3.14"

    def test_bool_true(self):
        assert _lua(True) == "true"

    def test_bool_false(self):
        assert _lua(False) == "false"

    def test_none(self):
        assert _lua(None) == "null"


# ---------------------------------------------------------------------------
# _lua – string escaping
# ---------------------------------------------------------------------------

class TestLuaStringEscaping:
    def test_backslash_doubled(self):
        # single \ becomes \\
        result = _lua("a\\b")
        assert result == "'a\\\\b'"

    def test_newline_becomes_double_backslash(self):
        # \n becomes \\ (two chars: backslash-backslash)
        result = _lua("line1\nline2")
        assert result == "'line1\\\\line2'"

    def test_carriage_return_escaped(self):
        result = _lua("a\rb")
        assert result == "'a\\rb'"

    def test_single_quote_escaped(self):
        result = _lua("it's")
        assert result == "'it\\'s'"

    def test_combined_escaping(self):
        result = _lua("a\nb\\c'd")
        # first: \\ becomes \\\\
        # then: \n becomes \\
        # then: ' becomes \'
        assert "\\\\\\\\c" not in result  # sanity: not quadrupled again
        assert "\\'" in result


# ---------------------------------------------------------------------------
# _lua – collections
# ---------------------------------------------------------------------------

class TestLuaCollections:
    def test_empty_dict(self):
        assert _lua({}) == "{}"

    def test_empty_list(self):
        assert _lua([]) == "{}"

    def test_simple_dict_contains_keys(self):
        result = _lua({"name": "Anna", "grade": 3})
        assert "name = 'Anna'" in result
        assert "grade = 3" in result

    def test_simple_list_contains_values(self):
        result = _lua(["a", "b"])
        assert "'a'" in result
        assert "'b'" in result

    def test_nested_dict(self):
        result = _lua({"person": {"name": "Bob"}})
        assert "'Bob'" in result
        assert "name = 'Bob'" in result

    def test_dict_with_list_value(self):
        result = _lua({"items": [1, 2, 3]})
        assert "items = " in result
        assert "1" in result

    def test_list_of_dicts(self):
        result = _lua([{"x": 1}, {"x": 2}])
        assert "x = 1" in result
        assert "x = 2" in result

    def test_indentation_increases_for_nested(self):
        result = _lua({"a": {"b": "c"}}, ind=0)
        lines = result.split("\n")
        # outer key at 2 spaces, inner at 4 spaces
        assert any(line.startswith("  a") for line in lines)

    def test_list_outer_brace(self):
        result = _lua([1, 2])
        assert result.startswith("{")
        assert result.endswith("}")


# ---------------------------------------------------------------------------
# _numeric_or_str
# ---------------------------------------------------------------------------

class TestNumericOrStr:
    def test_none_returns_none(self):
        assert _numeric_or_str(None) is None

    def test_zero(self):
        assert _numeric_or_str("0") == 0

    def test_single_digit_returns_int(self):
        assert _numeric_or_str("3") == 3
        assert isinstance(_numeric_or_str("3"), int)

    def test_nine_returns_int(self):
        assert _numeric_or_str("9") == 9

    def test_ten_returns_string(self):
        assert _numeric_or_str("10") == "10"
        assert isinstance(_numeric_or_str("10"), str)

    def test_whole_float_in_range_returns_int(self):
        assert _numeric_or_str("3.0") == 3
        assert isinstance(_numeric_or_str("3.0"), int)

    def test_non_whole_float_returns_string(self):
        result = _numeric_or_str("3.5")
        assert result == "3.5"
        assert isinstance(result, str)

    def test_comma_decimal_treated_as_dot(self):
        result = _numeric_or_str("3,0")
        assert result == 3

    def test_comma_non_whole_returns_string(self):
        result = _numeric_or_str("3,5")
        assert result == "3.5"

    def test_string_text_returned_unchanged(self):
        assert _numeric_or_str("gut") == "gut"

    def test_empty_string_returned_as_string(self):
        result = _numeric_or_str("")
        assert isinstance(result, str)

    def test_leading_trailing_spaces_stripped(self):
        assert _numeric_or_str("  5  ") == 5

    def test_negative_out_of_range_returns_string(self):
        result = _numeric_or_str("-1")
        assert result == "-1"
        assert isinstance(result, str)
