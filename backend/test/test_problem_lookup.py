import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.leetcode_source import _resolve_slug, normalize_question


class ProblemIndexTests(unittest.TestCase):
    def test_uses_frontend_problem_number_not_internal_database_id(self):
        index = {"stat_status_pairs": [
            {"stat": {"question_id": 9021, "frontend_question_id": 1, "question__title_slug": "two-sum"}}
        ]}
        self.assertEqual(_resolve_slug(index, 1), "two-sum")
        self.assertIsNone(_resolve_slug(index, 9021))


class ProblemNormalizationTests(unittest.TestCase):
    def test_normalizes_and_sanitizes_source_content(self):
        question = {
            "questionId": "1", "title": "Two Sum", "titleSlug": "two-sum",
            "content": "<p>Return <strong>two</strong> indices.</p><script>alert(1)</script><pre>nums = [2,7]</pre><p>Constraints:</p><ul><li>2 &lt;= n</li></ul>",
            "difficulty": "Easy", "isPaidOnly": False,
            "topicTags": [{"name": "Array", "slug": "array"}],
            "sampleTestCase": "nums = [2,7]", "metaData": "{}", "stats": "{}",
        }
        result = normalize_question(1, question)
        self.assertEqual(result["title"], "Two Sum")
        self.assertEqual(result["topic_tags"], ["Array"])
        self.assertNotIn("<script>", result["statement_html"])
        self.assertEqual(result["examples"], ["nums = [2,7]"])
        self.assertTrue(result["constraints"])
        self.assertEqual(result["canonical_url"], "https://leetcode.com/problems/two-sum/")


class APIContractTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_invalid_problem_numbers_are_rejected_before_fetch(self):
        for number in ("0", "-1", "1.5", "abc"):
            self.assertEqual(self.client.get(f"/api/problems/{number}").status_code, 400)

    def test_independent_proficiency_axes_are_preserved(self):
        response = self.client.post("/api/learner-config/validate", json={
            "language": "java",
            "dsa_proficiency": "beginner",
            "programming_proficiency": "advanced",
        })
        self.assertEqual(response.status_code, 200)
        profile = response.json()["profile"]
        self.assertEqual(profile["dsa_proficiency"], "beginner")
        self.assertEqual(profile["programming_proficiency"], "advanced")
        self.assertFalse(profile["syntax_support"])

    def test_beginner_programming_enables_syntax_explanations(self):
        response = self.client.post("/api/learner-config/validate", json={
            "language": "cpp",
            "dsa_proficiency": "advanced",
            "programming_proficiency": "beginner",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["profile"]["syntax_support"])


if __name__ == "__main__":
    unittest.main()
