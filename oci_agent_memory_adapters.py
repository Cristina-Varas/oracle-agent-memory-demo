from collections.abc import Sequence
from typing import Any

import numpy as np
from langchain_oci import ChatOCIGenAI, OCIGenAIEmbeddings
from oracleagentmemory.apis.llms.llm import LlmResponse


class OCIGenAIEmbedder:
    def __init__(self, embeddings: OCIGenAIEmbeddings) -> None:
        self.embeddings = embeddings

    def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        if is_query:
            vectors = [self.embeddings.embed_query(text) for text in texts]
        else:
            vectors = self.embeddings.embed_documents(texts)
        return np.asarray(vectors, dtype=np.float32)

    async def embed_async(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        return self.embed(texts, is_query=is_query)


class OCIChatLlm:
    def __init__(self, chat: ChatOCIGenAI) -> None:
        self.chat = chat

    def generate(
        self,
        prompt: str | Sequence[dict[str, str]],
        *,
        response_json_schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> LlmResponse:
        messages = self._to_messages(prompt)
        response = self.chat.invoke(messages, **kwargs)
        return LlmResponse(text=str(response.content))

    async def generate_async(
        self,
        prompt: str | Sequence[dict[str, str]],
        *,
        response_json_schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> LlmResponse:
        return self.generate(
            prompt,
            response_json_schema=response_json_schema,
            **kwargs,
        )

    def _to_messages(self, prompt: str | Sequence[dict[str, str]]) -> list[tuple[str, str]]:
        if isinstance(prompt, str):
            return [("user", prompt)]

        messages = []
        for message in prompt:
            messages.append((message["role"], message["content"]))
        return messages
