import abc
import os
import re
import httpx
from app.config import settings

class TranslationProvider(abc.ABC):
    @abc.abstractmethod
    async def translate(self, text: str, style: str) -> str:
        """
        Translates text into natural Japanese for TTS voice synthesis.
        """
        pass

class OpenAICompatibleTranslationProvider(TranslationProvider):
    async def translate(self, text: str, style: str) -> str:
        # Resolve config
        api_base = settings.translation_api_base or os.getenv("TRANSLATION_API_BASE", "")
        api_key = settings.translation_api_key or os.getenv("TRANSLATION_API_KEY", "")
        model = settings.translation_model or os.getenv("TRANSLATION_MODEL", "gpt-3.5-turbo")

        if not api_base or not api_key:
            raise ValueError("未配置翻译服务，请先配置翻译 API 或关闭自动翻译。")

        # Clean URL path for chat completions endpoint
        url = api_base
        if not url.endswith("/chat/completions") and not url.endswith("/chat/completions/"):
            url = url.rstrip("/") + "/chat/completions"

        # Extract tags matching <|...|> to protect them during translation
        tags = re.findall(r"(<\|.*?\|>)", text)
        masked_text = text
        for idx, tag in enumerate(tags):
            # We replace each instance sequentially with a unique placeholder
            masked_text = masked_text.replace(tag, f"__TAG_{idx}__", 1)

        # Construct prompt exactly as requested in C
        prompt = (
            "Translate the following text into natural Japanese for TTS voice synthesis.\n"
            "Preserve all tags in the form <|...|> exactly.\n"
            "Do not translate, delete, or rewrite control tags.\n"
            "Do not explain.\n"
            "Do not add quotation marks.\n"
            "Only output the Japanese result.\n"
            f"Style: {style}\n"
            f"Text: {masked_text}"
        )

        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code != 200:
                    raise RuntimeError(
                        f"翻译服务接口返回错误（HTTP {response.status_code}）。"
                    )

                res_data = response.json()
                translated = res_data["choices"][0]["message"]["content"].strip()

                # Clean outer quotation marks if any were added
                if (translated.startswith('"') and translated.endswith('"')) or (translated.startswith('「') and translated.endswith('」')):
                    translated = translated[1:-1].strip()

                # Restore original tags
                for idx, tag in enumerate(tags):
                    # Search case-insensitively and replace placeholder back to tag
                    pattern = re.compile(rf"__TAG_{idx}__", re.IGNORECASE)
                    translated = pattern.sub(tag, translated)

                return translated

        except httpx.RequestError as exc:
            raise RuntimeError("无法连接到翻译服务。") from exc

def get_translation_provider() -> TranslationProvider:
    provider_name = settings.translation_provider or os.getenv("TRANSLATION_PROVIDER", "openai_compatible")
    if provider_name == "openai_compatible":
        return OpenAICompatibleTranslationProvider()
    else:
        raise ValueError(f"Unsupported translation provider: {provider_name}")
