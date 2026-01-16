"""Tests for utils module."""

import pytest

from csvnorm.utils import (
    extract_filename_from_url,
    is_url,
    to_snake_case,
    validate_delimiter,
    validate_url,
)


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
        assert (
            to_snake_case("Trasporto Pubblico Locale.csv")
            == "trasporto_pubblico_locale"
        )


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


class TestIsUrl:
    """Tests for is_url function."""

    def test_http_url(self):
        assert is_url("http://example.com/data.csv") is True

    def test_https_url(self):
        assert is_url("https://example.com/data.csv") is True

    def test_ftp_url(self):
        assert is_url("ftp://example.com/data.csv") is False

    def test_file_url(self):
        assert is_url("file:///path/to/file.csv") is False

    def test_local_path(self):
        assert is_url("/path/to/file.csv") is False
        assert is_url("./file.csv") is False
        assert is_url("file.csv") is False

    def test_url_without_protocol(self):
        assert is_url("example.com/data.csv") is False


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_http(self):
        validate_url("http://example.com/data.csv")  # Should not raise

    def test_valid_https(self):
        validate_url("https://example.com/data.csv")  # Should not raise

    def test_invalid_ftp(self):
        with pytest.raises(ValueError, match="Only HTTP/HTTPS URLs"):
            validate_url("ftp://example.com/data.csv")

    def test_invalid_file(self):
        with pytest.raises(ValueError, match="Only HTTP/HTTPS URLs"):
            validate_url("file:///path/to/file.csv")


class TestExtractFilenameFromUrl:
    """Tests for extract_filename_from_url function."""

    def test_basic_csv_url(self):
        assert extract_filename_from_url("https://example.com/data.csv") == "data"

    def test_url_with_path(self):
        assert (
            extract_filename_from_url("https://example.com/path/to/data.csv") == "data"
        )

    def test_url_without_extension(self):
        assert extract_filename_from_url("https://example.com/data") == "data"

    def test_url_with_query_params(self):
        assert (
            extract_filename_from_url("https://example.com/data.csv?v=2&format=csv")
            == "data"
        )

    def test_url_with_url_encoding(self):
        # %20 = space
        result = extract_filename_from_url("https://example.com/My%20Data%20File.csv")
        assert result == "my_data_file"

    def test_url_with_complex_encoding(self):
        url = "https://example.com/Trasporto%20Pubblico%20Locale.csv"
        assert extract_filename_from_url(url) == "trasporto_pubblico_locale"

    def test_empty_path(self):
        assert extract_filename_from_url("https://example.com/") == "data"

    def test_root_url(self):
        assert extract_filename_from_url("https://example.com") == "data"
