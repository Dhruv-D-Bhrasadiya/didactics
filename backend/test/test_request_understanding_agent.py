import json
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError
from pydantic import SecretStr

from backend.app.agents.intent_analyzer_agent import RequestUnderstandingAgent
from backend.app.agents.run_artifacts import save_run_artifact
from backend.app.config import Settings
from backend.app.schemas import AgentExecutionTrace, RequestUnderstanding, TokenUsage


VALID_ANALYSIS = {
    "request_summary": "Learn binary search in Java",
    "request_type": "learn",
    "domain": "computer science",
    "subdomain": "algorithms",
    "topic": "binary search",
    "subtopics": ["sorted arrays", "midpoint calculation"],
    "modules": ["algorithm", "implementation", "complexity"],
    "roadmap": ["explain prerequisites", "walk through algorithm", "implement"],
    "learning_goal": "Understand and implement binary search in Java",
    "learning_objectives": ["implement binary search", "explain logarithmic time"],
    "learner_level": "beginner",
    "audience": "beginner programmer",
    "prior_knowledge": [],
    "assumed_prerequisites": ["basic Java syntax"],
    "explanation_depth": "detailed",
    "degree_of_explanation": "detailed",
    "concepts": ["sorted arrays", "binary search loop", "complexity"],
    "concept_order": ["sorted arrays", "binary search loop", "complexity"],
    "concept_dependencies": {"binary search loop": ["sorted arrays"]},
    "deliverables": ["Java implementation", "worked example"],
    "preferred_format": ["explanation", "code"],
    "programming_language": "Java",
    "constraints": ["Use Java"],
    "out_of_scope": [],
    "is_actionable": True,
    "ambiguity_level": "none",
    "clarification_needed": False,
    "clarification_questions": [],
    "missing_information": [],
    "assumptions": [],
    "confidence": 0.96,
    "decision_summary": "The request explicitly asks for a Java binary search lesson.",
}


class FakeLLM:
    """Provide a configurable language-model double for integration-style tests.

    It records invocation messages and returns content with optional usage
    metadata for validating traces.

    Example:
        llm = FakeLLM('{"topic": "binary search"}', {"input_tokens": 10})
    """

    def __init__(self, content, usage=None):
        """Set the model content and optional token metadata.

        Args:
            content: Value returned as response content.
            usage: Optional token-usage mapping attached to the response.

        Returns:
            None: Initializes the fake model and its invocation history.

        Example:
            llm = FakeLLM("{}", {"input_tokens": 10})
        """
        self.content = content
        self.usage = usage or {}
        self.calls = []

    def invoke(self, messages):
        """Record a prompt and return the configured response wrapper.

        Args:
            messages: Role/content message sequence supplied by the agent.

        Returns:
            SimpleNamespace: Response content and usage metadata.

        Example:
            response = llm.invoke([("user", "Teach binary search")])
        """
        self.calls.append(messages)
        return SimpleNamespace(
            content=self.content,
            usage_metadata=self.usage,
        )


class RequestUnderstandingAgentTests(unittest.TestCase):
    """Verify Stage 1 analysis, validation, artifacts, and CLI outcomes.

    These tests exercise request interpretation, trace details, schema rules,
    artifact serialization, and command-line success and failure handling.

    Example:
        python -m unittest backend.test.test_request_understanding_agent
    """

    def test_completes_all_stage_one_tasks_in_one_model_call(self):
        """Verify one model call returns the complete structured analysis.

        Args:
            None.

        Returns:
            None: Assertions pass when analysis and usage trace are complete.

        Example:
            python -m unittest backend.test.test_request_understanding_agent.RequestUnderstandingAgentTests.test_completes_all_stage_one_tasks_in_one_model_call
        """
        llm = FakeLLM(
            json.dumps(VALID_ANALYSIS, indent=2),
            {"input_tokens": 500, "output_tokens": 240, "total_tokens": 740},
        )
        agent = RequestUnderstandingAgent(
            "test-model", ["test-key"], lambda *_: llm, "groq"
        )

        result, trace = agent.analyze_with_trace(
            "Teach me binary search in Java."
        )

        self.assertIsInstance(result, RequestUnderstanding)
        self.assertEqual(result.learner_level, "beginner")
        self.assertEqual(result.concept_order[0], "sorted arrays")
        self.assertEqual(result.programming_language, "Java")
        self.assertEqual(len(llm.calls), 1)
        self.assertIn("RequestUnderstanding", llm.calls[0][1][1])
        self.assertIn("binary search", trace.raw_model_output)
        self.assertEqual(trace.parsed_output["topic"], "binary search")
        self.assertEqual(trace.provider, "groq")
        self.assertEqual(trace.token_usage.total_tokens, 740)

    def test_vague_request_is_representable_without_inventing_a_topic(self):
        """Verify vague requests can request clarification without a topic.

        Args:
            None.

        Returns:
            None: Assertions pass when the schema preserves uncertainty.

        Example:
            python -m unittest backend.test.test_request_understanding_agent.RequestUnderstandingAgentTests.test_vague_request_is_representable_without_inventing_a_topic
        """
        vague_analysis = {
            "request_summary": "The user wants to learn but has not chosen a subject.",
            "request_type": "unclear",
            "topic": None,
            "is_actionable": False,
            "ambiguity_level": "high",
            "clarification_needed": True,
            "clarification_questions": ["What topic would you like to learn?"],
            "missing_information": ["topic"],
            "confidence": 0.2,
            "decision_summary": "No learning topic is specified.",
        }

        result = RequestUnderstanding.model_validate(vague_analysis)

        self.assertIsNone(result.topic)
        self.assertEqual(result.learner_level, "unknown")
        self.assertEqual(len(result.clarification_questions), 1)

    def test_schema_rejects_missing_clarification_and_out_of_range_confidence(self):
        """Verify the schema rejects inconsistent clarification and confidence.

        Args:
            None.

        Returns:
            None: Assertions pass when both invalid payloads fail validation.

        Example:
            python -m unittest backend.test.test_request_understanding_agent.RequestUnderstandingAgentTests.test_schema_rejects_missing_clarification_and_out_of_range_confidence
        """
        invalid_clarification = {
            "request_summary": "Unclear request",
            "request_type": "unclear",
            "topic": None,
            "clarification_needed": True,
            "clarification_questions": [],
            "confidence": 0.5,
            "decision_summary": "Topic is unknown.",
        }
        with self.assertRaises(ValidationError):
            RequestUnderstanding.model_validate(invalid_clarification)

        invalid_confidence = {
            "request_summary": "Learn binary search",
            "request_type": "learn",
            "topic": "binary search",
            "confidence": 1.2,
            "decision_summary": "Topic is stated.",
        }
        with self.assertRaises(ValidationError):
            RequestUnderstanding.model_validate(
                invalid_confidence
            )

    def test_run_artifact_filename_and_json_include_model_and_timestamp(self):
        """Verify saved artifacts include a safe model label and JSON payload.

        Args:
            None.

        Returns:
            None: Assertions pass when filename and serialized data are correct.

        Example:
            python -m unittest backend.test.test_request_understanding_agent.RequestUnderstandingAgentTests.test_run_artifact_filename_and_json_include_model_and_timestamp
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            path = save_run_artifact(
                "gemini",
                "models/gemini-3.6-flash",
                {"run": {"provider": "gemini", "model_name": "models/gemini-3.6-flash"}},
                Path(temp_dir),
                run_id="12345678abcdef00",
            )

            self.assertRegex(
                path.name,
                r"^\d{8}T\d{12}Z_gemini_models_gemini-3\.6-flash_[0-9a-f]{8}\.json$",
            )
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["run"]["provider"], "gemini")

    def test_cli_saves_successful_run_record(self):
        """Verify a successful CLI run saves the analysis and execution trace.

        Args:
            None.

        Returns:
            None: Assertions pass when the CLI saves the selected run details.

        Example:
            python -m unittest backend.test.test_request_understanding_agent.RequestUnderstandingAgentTests.test_cli_saves_successful_run_record
        """
        import main

        class FakeAgent:
            """Supply predictable analysis and trace data to the CLI test.

            Example:
                agent = FakeAgent()
                analysis, trace = agent.analyze_with_trace("Teach binary search")
            """

            api_keys = ["secret-key"]

            def analyze_with_trace(self, query):
                """Return canned structured output and remember the query.

                Args:
                    query: Learner request passed by the CLI.

                Returns:
                    tuple[RequestUnderstanding, AgentExecutionTrace]: Test result
                        and corresponding trace.

                Example:
                    analysis, trace = agent.analyze_with_trace("Teach binary search")
                """
                self.received_query = query
                return RequestUnderstanding.model_validate(VALID_ANALYSIS), AgentExecutionTrace(
                    agent_name="request_understanding",
                    provider="groq",
                    model_name="org/model-under-test",
                    request_messages=[],
                    raw_model_output=json.dumps(VALID_ANALYSIS),
                    parsed_output=VALID_ANALYSIS,
                    token_usage=TokenUsage(input_tokens=30, output_tokens=20, total_tokens=50),
                    duration_ms=10,
                    attempt_count=1,
                )

        settings = Settings(
            groq_api_key=SecretStr("groq-key"),
            groq_model="configured-model",
        )
        fake_agent = FakeAgent()
        with (
            patch("sys.argv", [
                "main.py",
                "--provider",
                "groq",
                "--model",
                "org/model-under-test",
                "--query",
                "Teach binary search",
            ]),
            patch.object(main, "get_settings", return_value=settings),
            patch.object(main, "create_request_understanding_agent", return_value=fake_agent),
            patch.object(main, "save_run_artifact", return_value=Path("debug/run.json")) as save,
            redirect_stdout(io.StringIO()),
        ):
            result_code = main.main()

        self.assertEqual(result_code, 0)
        saved_provider, saved_model, artifact = save.call_args.args
        self.assertEqual((saved_provider, saved_model), ("groq", "org/model-under-test"))
        self.assertEqual(artifact["analysis"]["topic"], "binary search")
        self.assertEqual(artifact["trace"]["token_usage"]["total_tokens"], 50)
        self.assertEqual(artifact["run"]["request"], "Teach binary search")
        self.assertEqual(fake_agent.received_query, "Teach binary search")

    def test_cli_saves_failure_record_before_returning_nonzero(self):
        """Verify a configuration failure is recorded before CLI exit code one.

        Args:
            None.

        Returns:
            None: Assertions pass when the failure artifact contains the error.

        Example:
            python -m unittest backend.test.test_request_understanding_agent.RequestUnderstandingAgentTests.test_cli_saves_failure_record_before_returning_nonzero
        """
        import main

        settings = Settings(groq_api_key=None, groq_model="configured-model")
        with (
            patch("sys.argv", ["main.py", "--provider", "groq"]),
            patch.object(main, "get_settings", return_value=settings),
            patch.object(
                main,
                "create_request_understanding_agent",
                side_effect=ValueError("No API key is configured"),
            ),
            patch.object(main, "save_run_artifact", return_value=Path("debug/error.json")) as save,
            redirect_stderr(io.StringIO()),
        ):
            result_code = main.main()

        self.assertEqual(result_code, 1)
        self.assertEqual(save.call_args.args[0:2], ("groq", "configured-model"))
        self.assertEqual(save.call_args.args[2]["run"]["error"]["type"], "ValueError")
        self.assertIsNone(save.call_args.args[2]["trace"])


if __name__ == "__main__":
    unittest.main()
