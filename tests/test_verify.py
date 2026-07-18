from __future__ import annotations

import unittest

from conjecture_records.verify import UnsafeCommand, parse_allowed_command


class VerifyPolicyTests(unittest.TestCase):
    def test_python_checker_allowed(self) -> None:
        cwd, argv, environment = parse_allowed_command("PYTHONDONTWRITEBYTECODE=1 python3 checkers/replay.py")
        self.assertEqual(str(cwd), ".")
        self.assertEqual(argv, ["python3", "checkers/replay.py"])
        self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")

    def test_lean_target_allowed(self) -> None:
        cwd, argv, _ = parse_allowed_command("cd lean && lake build Target")
        self.assertEqual(str(cwd), "lean")
        self.assertEqual(argv, ["lake", "build", "Target"])

    def test_shell_and_traversal_rejected(self) -> None:
        for command in (
            "python3 checker.py; rm -rf x",
            "python3 ../private.py",
            "python3 checker.py | tee result",
            "curl https://example.test",
            "python3 $(whoami).py",
        ):
            with self.subTest(command=command), self.assertRaises(UnsafeCommand):
                parse_allowed_command(command)


if __name__ == "__main__":
    unittest.main()
