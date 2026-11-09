import unittest
from types import SimpleNamespace

from pydantic import SecretStr

from backend.app.agents.intent_analyzer_agent import (
	IntentAnalysis,
	IntentAnalyzerAgent,
	create_intent_analyzer_agent,
)
from backend.app.agents.factory import resolve_agent_config
from backend.app.agents.utils import ModelResponseError
from backend.app.config import Settings


VALID_JSON = """{
	"request_summary": "Learn binary search",
	"request_type": "learn",
	"domain": "computer science",
	"subdomain": "algorithms",
	"topic": "binary search",
	"subtopics": ["sorted arrays"],
	"modules": ["algorithm", "complexity"],
	"roadmap": ["explain", "implement", "practice"],
	"learning_goal": "Understand and implement binary search",
	"learning_objectives": ["implement binary search"],
	"learner_level": "beginner",
	"audience": "beginner programmer",
	"prior_knowledge": [],
	"assumed_prerequisites": ["arrays"],
	"explanation_depth": "detailed",
	"degree_of_explanation": "detailed",
	"concepts": ["sorted arrays", "binary search loop"],
	"concept_order": ["sorted arrays", "binary search loop"],
	"concept_dependencies": {"binary search loop": ["sorted arrays"]},
	"deliverables": ["worked example"],
	"preferred_format": ["explanation", "code"],
	"programming_language": "Java",
	"constraints": ["Use Java"],
	"out_of_scope": [],
	"is_actionable": true,
	"ambiguity_level": "none",
	"clarification_needed": false,
	"clarification_questions": [],
	"missing_information": [],
	"assumptions": [],
	"confidence": 0.96,
	"decision_summary": "The request asks to learn binary search."
}"""


class FakeLLM:
	"""Provide a programmable model double for agent behavior tests.

	The instance records messages and can return a response or raise an error.

	Example:
		llm = FakeLLM(response='{"topic": "binary search"}')
	"""

	def __init__(self, response=None, error=None):
		"""Configure the response or exception produced by this fake model.

		Args:
			response: Content returned by ``invoke`` when no error is set.
			error: Optional exception raised by ``invoke``.

		Returns:
			None: Initializes the fake model and its call history.

		Example:
			llm = FakeLLM(response="{}")
		"""
		self.response = response
		self.error = error
		self.messages = []

	def invoke(self, messages):
		"""Record messages and return the configured response or error.

		Args:
			messages: Role/content message sequence supplied by the agent.

		Returns:
			SimpleNamespace: Response wrapper containing the configured content.

		Raises:
			Exception: The configured error, when present.

		Example:
			response = llm.invoke([("user", "Explain binary search")])
		"""
		self.messages.append(messages)
		if self.error:
			raise self.error
		return SimpleNamespace(content=self.response)


class IntentAnalyzerAgentTests(unittest.TestCase):
	"""Verify the intent-analyzer compatibility API and provider configuration.

	The tests cover structured parsing, traces, API-key rotation, validation,
	and provider-specific factory behavior.

	Example:
		python -m unittest backend.test.test_intent_analyzer_agent
	"""

	def test_analyze_returns_validated_intent(self):
		"""Verify analysis returns a validated intent and sends the query.

		Args:
			None.

		Returns:
			None: Assertions pass if result validation and prompt inclusion work.

		Example:
			python -m unittest backend.test.test_intent_analyzer_agent.IntentAnalyzerAgentTests.test_analyze_returns_validated_intent
		"""
		llm = FakeLLM(VALID_JSON)
		agent = IntentAnalyzerAgent("test-model", ["key"], lambda *_: llm)

		result = agent.analyze("Teach me binary search")

		self.assertIsInstance(result, IntentAnalysis)
		self.assertEqual(result.topic, "binary search")
		self.assertIn("Teach me binary search", llm.messages[0][1][1])

	def test_analyze_accepts_json_markdown_fence(self):
		"""Verify JSON enclosed in a Markdown fence is accepted.

		Args:
			None.

		Returns:
			None: Assertions pass when fenced JSON is parsed successfully.

		Example:
			python -m unittest backend.test.test_intent_analyzer_agent.IntentAnalyzerAgentTests.test_analyze_accepts_json_markdown_fence
		"""
		agent = IntentAnalyzerAgent("test-model", ["key"], lambda *_: FakeLLM(f"```json\n{VALID_JSON}\n```"))

		self.assertEqual(agent.analyze("Explain it").domain, "computer science")

	def test_analyze_with_trace_preserves_invalid_model_output(self):
		"""Verify malformed output remains available in the raised error trace.

		Args:
			None.

		Returns:
			None: Assertions pass when the trace retains raw output and no parse.

		Example:
			python -m unittest backend.test.test_intent_analyzer_agent.IntentAnalyzerAgentTests.test_analyze_with_trace_preserves_invalid_model_output
		"""
		response = "not json"
		agent = IntentAnalyzerAgent(
			"test-model", ["key"], lambda *_: FakeLLM(response)
		)

		with self.assertRaises(ModelResponseError) as raised:
			agent.analyze_with_trace("Explain it")

		self.assertEqual(raised.exception.trace.raw_model_output, response)
		self.assertEqual(raised.exception.trace.parsed_output, {})

	def test_rotates_once_per_key_on_rotatable_error(self):
		"""Verify a retryable failure rotates to the next configured key.

		Args:
			None.

		Returns:
			None: Assertions pass when one rotation enables successful analysis.

		Example:
			python -m unittest backend.test.test_intent_analyzer_agent.IntentAnalyzerAgentTests.test_rotates_once_per_key_on_rotatable_error
		"""
		llms = {
			"first": FakeLLM(error=RuntimeError("429 quota exceeded")),
			"second": FakeLLM(VALID_JSON),
		}
		built_keys = []

		def builder(key, _model):
			"""Return a fake model for a key and record which key was built.

			Args:
				key: API key mapped to a fake model.
				_model: Model identifier, unused by this test builder.

			Returns:
				FakeLLM: Model double associated with ``key``.

			Example:
				llm = builder("first", "test-model")
			"""
			built_keys.append(key)
			return llms[key]

		agent = IntentAnalyzerAgent("test-model", ["first", "second"], builder)

		result = agent.analyze("Explain it")

		self.assertEqual(result.topic, "binary search")
		self.assertEqual(built_keys, ["first", "second"])
		self.assertEqual(agent.current_key_index, 1)

	def test_non_rotatable_error_is_reraised(self):
		"""Verify non-retryable invocation errors propagate unchanged.

		Args:
			None.

		Returns:
			None: Assertions pass when the original error is reraised.

		Example:
			python -m unittest backend.test.test_intent_analyzer_agent.IntentAnalyzerAgentTests.test_non_rotatable_error_is_reraised
		"""
		agent = IntentAnalyzerAgent("test-model", ["key"], lambda *_: FakeLLM(error=ValueError("bad JSON")))

		with self.assertRaises(ValueError):
			agent.analyze("Explain it")

	def test_last_rotatable_error_is_reraised(self):
		"""Verify the final retryable error propagates after key exhaustion.

		Args:
			None.

		Returns:
			None: Assertions pass when the last key's error is raised.

		Example:
			python -m unittest backend.test.test_intent_analyzer_agent.IntentAnalyzerAgentTests.test_last_rotatable_error_is_reraised
		"""
		agent = IntentAnalyzerAgent(
			"test-model",
			["first", "second"],
			lambda key, _model: FakeLLM(error=RuntimeError(f"429 quota exceeded: {key}")),
		)

		with self.assertRaisesRegex(RuntimeError, "second"):
			agent.analyze("Explain it")

		self.assertEqual(agent.current_key_index, 1)

	def test_rejects_empty_query_and_keys(self):
		"""Verify an agent rejects missing keys and blank learner queries.

		Args:
			None.

		Returns:
			None: Assertions pass when both invalid inputs raise ValueError.

		Example:
			python -m unittest backend.test.test_intent_analyzer_agent.IntentAnalyzerAgentTests.test_rejects_empty_query_and_keys
		"""
		with self.assertRaises(ValueError):
			IntentAnalyzerAgent("test-model", [], lambda *_: FakeLLM())

		agent = IntentAnalyzerAgent("test-model", ["key"], lambda *_: FakeLLM(VALID_JSON))
		with self.assertRaises(ValueError):
			agent.analyze("  ")

	def test_factory_unwraps_secret_keys(self):
		"""Verify the factory unwraps configured secret keys in order.

		Args:
			None.

		Returns:
			None: Assertions pass when both keys and selected model are retained.

		Example:
			python -m unittest backend.test.test_intent_analyzer_agent.IntentAnalyzerAgentTests.test_factory_unwraps_secret_keys
		"""
		app_settings = Settings(
			gemini_api_key=SecretStr("primary"),
			gemini_api_key_fallback_1=SecretStr("fallback"),
		)

		agent = create_intent_analyzer_agent("gemini", "test-model", app_settings)

		self.assertEqual(agent.api_keys, ["primary", "fallback"])
		self.assertEqual(agent.model_name, "test-model")

	def test_groq_configuration_does_not_require_a_gemini_key(self):
		"""Verify Groq setup works with Groq credentials alone.

		Args:
			None.

		Returns:
			None: Assertions pass when Groq config resolves without Gemini keys.

		Example:
			python -m unittest backend.test.test_intent_analyzer_agent.IntentAnalyzerAgentTests.test_groq_configuration_does_not_require_a_gemini_key
		"""
		provider, model, keys, _ = resolve_agent_config(
			"groq",
			"qwen/experiment-model",
			Settings(groq_api_key=SecretStr("groq-key"), groq_model="groq-model"),
		)

		self.assertEqual(
			(provider, model, keys),
			("groq", "qwen/experiment-model", ["groq-key"]),
		)

	def test_gemini_and_groq_model_ids_are_selected_without_fallback(self):
		"""Verify exact Gemini and Groq model overrides are preserved.

		Args:
			None.

		Returns:
			None: Assertions pass when each provider returns its selected model.

		Example:
			python -m unittest backend.test.test_intent_analyzer_agent.IntentAnalyzerAgentTests.test_gemini_and_groq_model_ids_are_selected_without_fallback
		"""
		gemini = resolve_agent_config(
			"gemini",
			"models/gemini-experiment",
			Settings(gemini_api_key=SecretStr("gemini-key")),
		)
		groq = resolve_agent_config(
			"groq",
			"organization/groq-experiment",
			Settings(groq_api_key=SecretStr("groq-key")),
		)

		self.assertEqual((gemini[0], gemini[1], gemini[2]), (
			"gemini", "models/gemini-experiment", ["gemini-key"]
		))
		self.assertEqual((groq[0], groq[1], groq[2]), (
			"groq", "organization/groq-experiment", ["groq-key"]
		))


if __name__ == "__main__":
	unittest.main()
