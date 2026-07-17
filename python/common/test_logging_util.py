import logging
import unittest

from common.logging_util import get_logger


class GetLoggerTest(unittest.TestCase):
    def tearDown(self) -> None:
        for name in ("test.logger.one", "test.logger.level"):
            logger = logging.getLogger(name)
            logger.handlers.clear()

    def test_returns_logger_with_requested_name(self) -> None:
        logger = get_logger("test.logger.one")
        self.assertEqual(logger.name, "test.logger.one")

    def test_adds_exactly_one_handler(self) -> None:
        logger = get_logger("test.logger.one")
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)

    def test_calling_twice_does_not_duplicate_handlers(self) -> None:
        get_logger("test.logger.one")
        logger = get_logger("test.logger.one")
        self.assertEqual(len(logger.handlers), 1)

    def test_does_not_propagate_to_root(self) -> None:
        logger = get_logger("test.logger.one")
        self.assertFalse(logger.propagate)

    def test_handler_level_matches_requested_level(self) -> None:
        logger = get_logger("test.logger.level", level=logging.WARNING)
        self.assertEqual(logger.handlers[0].level, logging.WARNING)


if __name__ == "__main__":
    unittest.main()
