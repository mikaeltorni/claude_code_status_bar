"""Regression tests for status-bar value formatting."""

import unittest
from unittest import mock

import status_bar_format


class FormatTokensTests(unittest.TestCase):
    """Verify compact token-count formatting at unit boundaries."""

    def test_formats_plain_thousands_and_millions(self):
        self.assertEqual(status_bar_format.format_tokens(999), "999")
        self.assertEqual(status_bar_format.format_tokens(1_000), "1.0k")
        self.assertEqual(status_bar_format.format_tokens(63_249), "63.2k")
        self.assertEqual(status_bar_format.format_tokens(1_000_000), "1.0M")

    def test_truncates_fractional_tokens_before_formatting(self):
        self.assertEqual(status_bar_format.format_tokens(999.9), "999")

    def test_rejects_invalid_token_count(self):
        self.assertEqual(status_bar_format.format_tokens("not-a-number"), "")


class FormatResetTests(unittest.TestCase):
    """Verify relative reset-time formatting."""

    @mock.patch.object(status_bar_format.time, "time", return_value=1_000)
    def test_formats_hours_and_minutes(self, _mock_time):
        self.assertEqual(status_bar_format.format_reset(1_000 + 2 * 3_600 + 13 * 60), "2h13m")

    @mock.patch.object(status_bar_format.time, "time", return_value=1_000)
    def test_formats_sub_hour_and_expired_resets(self, _mock_time):
        self.assertEqual(status_bar_format.format_reset(1_000 + 59 * 60), "59m")
        self.assertEqual(status_bar_format.format_reset(1_000), "now")

    def test_rejects_invalid_timestamp(self):
        self.assertEqual(status_bar_format.format_reset("invalid"), "")


class FormatResetDayTests(unittest.TestCase):
    """Verify absolute weekly reset-time formatting."""

    @mock.patch.object(status_bar_format.time, "localtime", return_value=object())
    @mock.patch.object(status_bar_format.time, "strftime", return_value="Sat 22:22")
    def test_formats_reset_in_local_time(self, mock_strftime, mock_localtime):
        self.assertEqual(status_bar_format.format_reset_day("1700000000"), "Sat 22:22")
        mock_localtime.assert_called_once_with(1_700_000_000)
        mock_strftime.assert_called_once_with("%a %H:%M", mock_localtime.return_value)

    def test_rejects_invalid_timestamp(self):
        self.assertEqual(status_bar_format.format_reset_day(None), "")


if __name__ == "__main__":
    unittest.main()
