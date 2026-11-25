import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = (ROOT / os.environ.get("WRAP_TEXT_BIN", "build/wrap-text")).resolve()


class WrapTextTests(unittest.TestCase):
    def run_cli(self, data=b"", *arguments):
        return subprocess.run([str(BINARY), *arguments], input=data, capture_output=True)

    def assert_output(self, data, expected, *arguments):
        result = self.run_cli(data, *arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected)
        self.assertEqual(result.stderr, b"")

    def test_readme_example(self):
        self.assert_output(b"a short note for the notice board", b"a short note for\nthe notice board\n", "--width", "16")

    def test_synthetic_notice_and_input_unchanged(self):
        source = ROOT / "samples/note.txt"
        before = source.read_bytes()
        result = self.run_cli(b"", "--width", "32", str(source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, (ROOT / "samples/expected-32.txt").read_bytes())
        self.assertEqual(source.read_bytes(), before)

    def test_empty_and_whitespace_only(self):
        for data in (b"", b" \t\v\f", b"\n\r\n\n \t\n"):
            with self.subTest(data=data):
                self.assert_output(data, b"")

    def test_ascii_whitespace_and_line_endings(self):
        self.assert_output(b"one\ttwo\vthree\ffour\nfive\rsix\r\nseven", b"one two three four five six seven\n")

    def test_blank_lines_collapse_and_trim(self):
        self.assert_output(b"\n \t\r\none\ntwo\n\t\n\nthree\r\r\nfour\n\n", b"one two\n\nthree\n\nfour\n")

    def test_exact_width_and_width_one(self):
        self.assert_output(b"aa bb cc", b"aa bb\ncc\n", "--width", "5")
        self.assert_output(b"a b cc d", b"a\nb\ncc\nd\n", "--width", "1")

    def test_overlong_words_and_bounded_prefix_edges(self):
        for width in (1, 32, 72, 240):
            for length in (width, width + 1, 2 * width + 1, 100_000):
                with self.subTest(width=width, length=length):
                    word = b"x" * length
                    self.assert_output(b"a " + word + b" b", b"a\n" + word + b"\nb\n", "--width", str(width))

    def test_default_width_and_upper_bound(self):
        self.assert_output(b"a " * 37, b" ".join([b"a"] * 36) + b"\na\n")
        self.assert_output(b"x" * 240 + b" y", b"x" * 240 + b"\ny\n", "--width", "240")

    def test_explicit_stdin_and_leading_zero_width(self):
        self.assert_output(b"one two", b"one\ntwo\n", "--width", "0003", "-")

    def test_invalid_arguments(self):
        invalid = (("--width",), ("--width", "0"), ("--width", "241"), ("--width", "-2"),
                   ("--width", "+2"), ("--width", "2.0"), ("--width", "2x"), ("--width", ""),
                   ("--width", "9" * 100), ("--width", "2", "--width", "3"), ("--wat",),
                   ("one", "two"), ("--help", "extra"))
        for arguments in invalid:
            with self.subTest(arguments=arguments):
                result = self.run_cli(b"hello", *arguments)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertIn(b"usage:", result.stderr)

    def test_rejects_each_unsupported_byte(self):
        allowed = set(range(32, 127)) | {9, 10, 11, 12, 13}
        for byte in set(range(256)) - allowed:
            with self.subTest(byte=byte):
                result = self.run_cli(bytes([byte]))
                self.assertEqual(result.returncode, 1)
                self.assertIn(b"ASCII", result.stderr)

    def test_file_named_like_an_option(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "--note"
            source.write_bytes(b"alpha beta")
            result = subprocess.run([str(BINARY), "--width", "5", "--", "--note"], cwd=directory, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, b"alpha\nbeta\n")
            self.assertEqual(source.read_bytes(), b"alpha beta")

    def test_missing_file_and_input_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            for source in (str(Path(directory) / "missing"), directory):
                result = self.run_cli(b"", source)
                self.assertEqual(result.returncode, 1)
                self.assertIn(b"input", result.stderr)

    def test_help(self):
        result = self.run_cli(b"", "--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"default width: 72", result.stdout)
        self.assertEqual(result.stderr, b"")

    def test_closed_output_pipe(self):
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        try:
            result = subprocess.run([str(BINARY)], input=b"hello", stdout=write_fd, stderr=subprocess.PIPE)
        finally:
            os.close(write_fd)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"output error", result.stderr)

    @unittest.skipUnless(Path("/dev/full").exists(), "requires Linux /dev/full")
    def test_output_failure(self):
        with open("/dev/full", "wb") as output:
            result = subprocess.run([str(BINARY)], input=b"hello", stdout=output, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"output error", result.stderr)


if __name__ == "__main__":
    unittest.main()
