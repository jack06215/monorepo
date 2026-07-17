import unittest
from typing import Any
from unittest.mock import Mock

from langchain_core.callbacks import BaseCallbackManager
from langchain_core.runnables import RunnableConfig

from common.langchain_invoke import invoke_llm


def _factory_returning(runnable: Mock) -> Any:
    def factory(*, template: Any, chat: Any, parser: Any) -> Mock:
        return runnable

    return factory


class InvokeLlmSuccessTest(unittest.TestCase):
    def test_returns_chain_output_and_logs_start(self) -> None:
        runnable = Mock()
        runnable.invoke.return_value = "chain-output"
        logger = Mock()

        result = invoke_llm(
            template=Mock(),
            chat=Mock(),
            parser=Mock(),
            logger=logger,
            chain_factory=_factory_returning(runnable),
            input={"title": "my-title", "x": 1},
        )

        self.assertEqual(result, "chain-output")
        logger.info.assert_called_once()
        self.assertIn("my-title", logger.info.call_args.args)

    def test_input_data_passed_through_to_chain_invoke(self) -> None:
        runnable = Mock()
        runnable.invoke.return_value = "ok"

        invoke_llm(
            template=Mock(),
            chat=Mock(),
            parser=Mock(),
            logger=Mock(),
            chain_factory=_factory_returning(runnable),
            input={"title": "t", "x": 42},
        )

        called_input = runnable.invoke.call_args.args[0]
        self.assertEqual(called_input, {"title": "t", "x": 42})

    def test_explicit_title_overrides_input_title(self) -> None:
        runnable = Mock()
        runnable.invoke.return_value = "ok"
        logger = Mock()

        invoke_llm(
            template=Mock(),
            chat=Mock(),
            parser=Mock(),
            logger=logger,
            chain_factory=_factory_returning(runnable),
            input={"title": "from-input"},
            title="explicit-title",
        )

        self.assertIn("explicit-title", logger.info.call_args.args)

    def test_defaults_title_placeholder_when_none_given(self) -> None:
        runnable = Mock()
        runnable.invoke.return_value = "ok"
        logger = Mock()

        invoke_llm(
            template=Mock(),
            chat=Mock(),
            parser=Mock(),
            logger=logger,
            chain_factory=_factory_returning(runnable),
        )

        self.assertIn("<title>", logger.info.call_args.args)

    def test_wraps_callbacks_list_into_callback_manager_on_caller_config(self) -> None:
        runnable = Mock()
        runnable.invoke.return_value = "ok"
        config: RunnableConfig = {"tags": ["mytag"]}

        invoke_llm(
            template=Mock(),
            chat=Mock(),
            parser=Mock(),
            logger=Mock(),
            chain_factory=_factory_returning(runnable),
            config=config,
        )

        self.assertIsInstance(config.get("callbacks"), BaseCallbackManager)
        self.assertEqual(config["tags"], ["mytag"])


class InvokeLlmFailureTest(unittest.TestCase):
    def test_non_retryable_exception_propagates_and_is_logged(self) -> None:
        runnable = Mock()
        runnable.invoke.side_effect = RuntimeError("boom")
        logger = Mock()

        with self.assertRaises(RuntimeError):
            invoke_llm(
                template=Mock(),
                chat=Mock(),
                parser=Mock(),
                logger=logger,
                chain_factory=_factory_returning(runnable),
                input={"title": "failing-title"},
            )

        logger.exception.assert_called_once()
        self.assertIn("failing-title", logger.exception.call_args.args)
        runnable.invoke.assert_called_once()


if __name__ == "__main__":
    unittest.main()
