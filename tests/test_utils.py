"""Tests for utils module."""

import pytest

from csvnorm.utils import to_snake_case, validate_delimiter


class TestToSnakeCase:
    """Tests for to_snake_case function."""

    def test_basic_filename(self):
        assert to_snake_case("test.csv") == "test"

    def test_spaces(self):
        assert to_snake_case("My File Name.csv") == "my_file_name"

    def test_uppercase(self):
        assert to_snake_case("UPPERCASE.csv") == "uppercase"

    def test_mixed_case(self):
        assert to_snake_case("CamelCase.csv") == "camelcase"

    def test_special_chars(self):
        assert to_snake_case("file-with-dashes.csv") == "file_with_dashes"
        assert to_snake_case("file.with.dots.csv") == "file_with_dots"

    def test_multiple_underscores(self):
        assert to_snake_case("file___name.csv") == "file_name"

    def test_leading_trailing_underscores(self):
        assert to_snake_case("_file_.csv") == "file"

    def test_numbers(self):
        assert to_snake_case("file123.csv") == "file123"
        assert to_snake_case("123file.csv") == "123file"

    def test_no_extension(self):
        assert to_snake_case("filename") == "filename"

    def test_accented_chars(self):
        # Non-ascii chars should be replaced with underscore
        assert to_snake_case("Città.csv") == "citt"

    def test_real_world_example(self):
        assert to_snake_case("Trasporto Pubblico Locale.csv") == "trasporto_pubblico_locale"


class TestValidateDelimiter:
    """Tests for validate_delimiter function."""

    def test_valid_comma(self):
        validate_delimiter(",")  # Should not raise

    def test_valid_semicolon(self):
        validate_delimiter(";")  # Should not raise

    def test_valid_tab(self):
        validate_delimiter("\t")  # Should not raise

    def test_valid_pipe(self):
        validate_delimiter("|")  # Should not raise

    def test_invalid_empty(self):
        with pytest.raises(ValueError):
            validate_delimiter("")

    def test_invalid_multiple(self):
        with pytest.raises(ValueError):
            validate_delimiter(";;")
