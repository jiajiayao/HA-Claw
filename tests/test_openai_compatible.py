import unittest

from custom_components.haclaw.providers.openai_compatible import (
    ChatCompletionResult,
    OpenAICompatibleClient,
    extract_chat_completion_result,
    normalize_chat_completions_url,
    redact_secret,
)


class OpenAICompatibleClientTests(unittest.TestCase):
    def test_normalizes_root_base_url(self):
        self.assertEqual(
            normalize_chat_completions_url("https://api.deepseek.com"),
            "https://api.deepseek.com/v1/chat/completions",
        )

    def test_normalizes_versioned_base_url(self):
        self.assertEqual(
            normalize_chat_completions_url("https://api.moonshot.cn/v1/"),
            "https://api.moonshot.cn/v1/chat/completions",
        )

    def test_keeps_full_chat_completions_endpoint(self):
        self.assertEqual(
            normalize_chat_completions_url(
                "https://oneapi.example.com/openai/v1/chat/completions"
            ),
            "https://oneapi.example.com/openai/v1/chat/completions",
        )

    def test_builds_openai_compatible_payload(self):
        client = OpenAICompatibleClient(
            api_key="sk-test-secret",
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
        )

        payload = client.build_payload(
            [{"role": "user", "content": "你好"}],
            temperature=0.2,
            top_p=0.8,
            max_tokens=128,
        )

        self.assertEqual(payload["model"], "deepseek-chat")
        self.assertEqual(payload["messages"][0]["content"], "你好")
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["top_p"], 0.8)
        self.assertEqual(payload["max_tokens"], 128)

    def test_redacts_secrets_without_leaking_original_value(self):
        redacted = redact_secret("sk-test-secret")

        self.assertNotIn("sk-test-secret", redacted)
        self.assertTrue(redacted.startswith("sk-t"))
        self.assertTrue(redacted.endswith("cret"))

    def test_extracts_usage_from_openai_compatible_response(self):
        result = extract_chat_completion_result(
            {
                "choices": [{"message": {"content": "你好"}}],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 8,
                    "total_tokens": 20,
                },
            }
        )

        self.assertIsInstance(result, ChatCompletionResult)
        self.assertEqual(result.content, "你好")
        self.assertEqual(result.usage["total_tokens"], 20)


if __name__ == "__main__":
    unittest.main()
