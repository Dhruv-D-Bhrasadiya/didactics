import unittest
from pydantic import ValidationError
from backend.app.schemas.workflow import CodeVariant, ComplexityItem, GenerateSessionRequest

class WorkflowSchemaTests(unittest.TestCase):
    def test_request_rejects_invalid_problem_number(self):
        with self.assertRaises(ValidationError):
            GenerateSessionRequest(problem_number=0, language="python", dsa_proficiency="beginner", programming_proficiency="beginner")

    def test_complexity_schema_requires_derivations(self):
        with self.assertRaises(ValidationError):
            ComplexityItem(variant_id="v1", time_complexity="O(n)", time_derivation=[], space_complexity="O(1)", space_derivation=["constant"])

    def test_solution_variant_requires_code(self):
        with self.assertRaises(ValidationError):
            CodeVariant(variant_id="v1", algorithm_name="brute", strategy="x", intuition="x", steps=["x"], correctness_explanation="x", time_complexity_claim="O(n)", space_complexity_claim="O(1)")

if __name__ == "__main__":
    unittest.main()
