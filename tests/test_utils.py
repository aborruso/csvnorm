"""Tests for utils module."""

import ssl
import urllib.error
import zipfile

import pytest
import requests

from unittest.mock import Mock, patch

from csvnorm.utils import (
    build_zip_path,
    download_url_to_file,
    extract_filename_from_url,
    is_compressed_url,
    is_gzip_path,
    is_url,
    is_zip_path,
    resolve_zip_csv_entry,
    supports_http_range,
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


class TestIsCompressedUrl:
    """Tests for compressed URL detection."""

    def test_gzip_url(self):
        assert (
            is_compressed_url("https://example.com/data.csv.gz") is True
        )

    def test_zip_url(self):
        assert is_compressed_url("https://example.com/data.zip") is True

    def test_non_compressed_url(self):
        assert is_compressed_url("https://example.com/data.csv") is False


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


class TestSupportsHttpRange:
    """Tests for supports_http_range function."""

    @patch("csvnorm.utils.urllib.request.urlopen")
    def test_status_206(self, mock_urlopen):
        mock_response = Mock()
        mock_response.status = 206
        mock_response.headers = {}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        assert supports_http_range("https://example.com/data.csv") is True

    @patch("csvnorm.utils.urllib.request.urlopen")
    def test_accept_ranges_header(self, mock_urlopen):
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {"Accept-Ranges": "bytes"}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        assert supports_http_range("https://example.com/data.csv") is True

    @patch("csvnorm.utils.urllib.request.urlopen")
    def test_content_range_header(self, mock_urlopen):
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {"Content-Range": "bytes 0-0/100"}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        assert supports_http_range("https://example.com/data.csv") is True

    @patch("csvnorm.utils.urllib.request.urlopen")
    def test_no_range_support(self, mock_urlopen):
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        assert supports_http_range("https://example.com/data.csv") is False

    @patch("csvnorm.utils.urllib.request.urlopen")
    def test_urlopen_error(self, mock_urlopen):
        mock_urlopen.side_effect = OSError("boom")
        assert supports_http_range("https://example.com/data.csv") is False


class TestCompressedPathHelpers:
    """Tests for compressed path helpers."""

    def test_is_gzip_path(self, tmp_path):
        assert is_gzip_path(tmp_path / "data.csv.gz") is True
        assert is_gzip_path(tmp_path / "data.csv") is False

    def test_is_zip_path(self, tmp_path):
        assert is_zip_path(tmp_path / "data.zip") is True
        assert is_zip_path(tmp_path / "data.csv") is False

    def test_resolve_zip_csv_entry_single(self, tmp_path):
        zip_path = tmp_path / "data.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("data.csv", "a,b\n1,2\n")
            archive.writestr("readme.txt", "notes")

        entry = resolve_zip_csv_entry(zip_path)
        assert entry == "data.csv"
        zip_uri = build_zip_path(zip_path, entry)
        assert zip_uri.startswith("zip://")
        assert zip_uri.endswith("/data.csv")

    def test_resolve_zip_csv_entry_multiple(self, tmp_path):
        zip_path = tmp_path / "multi.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("a.csv", "a\n1\n")
            archive.writestr("b.csv", "b\n2\n")

        with pytest.raises(
            ValueError,
            match="The file contains more than one file. Extract the one you need",
        ):
            resolve_zip_csv_entry(zip_path)

    def test_resolve_zip_csv_entry_none(self, tmp_path):
        zip_path = tmp_path / "none.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("notes.txt", "notes")

        with pytest.raises(ValueError, match="no CSV"):
            resolve_zip_csv_entry(zip_path)


class TestDownloadUrlToFile:
    """Tests for download_url_to_file function."""

    @patch("csvnorm.utils.requests.get")
    @patch("csvnorm.utils.urllib.request.urlopen")
    def test_ssl_handshake_fallback(
        self, mock_urlopen, mock_requests_get, tmp_path
    ):
        ssl_error = ssl.SSLError("SSLV3_ALERT_HANDSHAKE_FAILURE")
        mock_urlopen.side_effect = urllib.error.URLError(ssl_error)

        mock_response = Mock()
        mock_response.iter_content.return_value = [b"one,", b"two\n"]
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        output_path = tmp_path / "download.csv"
        download_url_to_file("https://example.com/data.csv", output_path)

        assert output_path.read_bytes() == b"one,two\n"
        mock_requests_get.assert_called_once()

    @patch("csvnorm.utils._download_with_curl")
    @patch("csvnorm.utils._download_with_requests")
    @patch("csvnorm.utils.urllib.request.urlopen")
    def test_ssl_handshake_fallback_to_curl(
        self, mock_urlopen, mock_requests, mock_curl, tmp_path
    ):
        ssl_error = ssl.SSLError("SSLV3_ALERT_HANDSHAKE_FAILURE")
        mock_urlopen.side_effect = urllib.error.URLError(ssl_error)
        mock_requests.side_effect = requests.exceptions.SSLError("handshake failed")

        output_path = tmp_path / "download.csv"

        def _write_output(*_args, **_kwargs):
            output_path.write_bytes(b"ok\n")
            return output_path

        mock_curl.side_effect = _write_output

        download_url_to_file("https://example.com/data.csv", output_path)

        assert output_path.read_bytes() == b"ok\n"
        mock_curl.assert_called_once()
