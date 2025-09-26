"""HTTP client wrapper that mirrors the PotPlayer plugin behaviour."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib import request, error


@dataclass
class APIError(Exception):
    message: str
    response: Optional[Dict] = None

    def __str__(self) -> str:  # pragma: no cover - trivial wrapper
        return self.message


@dataclass
class APIClient:
    api_url: str
    api_key: str
    model: str
    user_agent: str
    delay_ms: int = 0
    retry_mode: int = 0
    context_cache_mode: str = "auto"

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request_with_retry(self, url: str, payload: Dict) -> Dict:
        data = json.dumps(payload).encode("utf-8")
        headers = self._build_headers()
        attempts = 0
        delay_seconds = max(0.0, self.delay_ms / 1000.0)

        while True:
            if attempts > 0:
                # Retry behaviour: mode 0 -> no retry, mode 1 -> retry once,
                # mode 2 -> infinite, mode 3 -> retry after delay for every
                # attempt.  The PotPlayer plugin delays the initial attempt
                # as well when retry mode is 3; we reproduce that behaviour
                # here.
                if self.retry_mode == 0 or (self.retry_mode == 1 and attempts > 1):
                    break
            if delay_seconds > 0 and (attempts == 0 and self.retry_mode == 3 or attempts > 0):
                time.sleep(delay_seconds)
            req = request.Request(url, data=data, headers=headers)
            try:
                with request.urlopen(req, timeout=60) as resp:
                    body = resp.read().decode("utf-8")
            except error.HTTPError as exc:
                body = exc.read().decode("utf-8") if exc.fp else ""
                try:
                    parsed = json.loads(body)
                except json.JSONDecodeError:
                    parsed = {"error": {"message": body or exc.reason}}
                raise APIError(parsed.get("error", {}).get("message", str(exc)), parsed)
            except error.URLError as exc:
                body = ""
                parsed = {"error": {"message": getattr(exc, "reason", str(exc))}}
            else:
                try:
                    parsed = json.loads(body)
                except json.JSONDecodeError as exc:
                    raise APIError(f"Failed to parse response JSON: {exc}") from exc
                return parsed

            attempts += 1
            if self.retry_mode in (0, 1) and attempts > self.retry_mode:
                raise APIError(parsed.get("error", {}).get("message", "Network error"), parsed)
            # For retry modes 2 and 3, continue until success.

    # --- Chat completions ---
    def translate_chat(self, system_message: str, user_message: str, temperature: float = 0.0) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": 1000,
            "temperature": temperature,
        }
        response = self._request_with_retry(self.api_url, payload)
        try:
            choices = response["choices"]
        except KeyError as exc:  # pragma: no cover - defensive
            raise APIError("Malformed response: missing 'choices' field", response) from exc
        if not choices:
            raise APIError("Empty response from the translation API", response)
        message = choices[0].get("message", {})
        content = message.get("content")
        if not content:
            raise APIError("Translation API returned no content", response)
        return str(content)

    # --- Responses endpoint with caching ---
    def _derive_responses_url(self) -> Optional[str]:
        url = self.api_url.rstrip("/")
        if not url:
            return None
        if "/responses" in url:
            return url
        marker = "/chat/completions"
        if marker in url:
            return url.replace(marker, "/responses")
        return f"{url}/responses"

    def translate_responses(
        self,
        system_message: str,
        instruction: str,
        context_segments: List[str],
        subtitle_text: str,
        temperature: float = 0.0,
    ) -> Optional[str]:
        if self.context_cache_mode == "off":
            return None
        responses_url = self._derive_responses_url()
        if not responses_url:
            return None

        content: List[Dict[str, str]] = [
            {"type": "input_text", "text": system_message, "cache_control": {"type": "ephemeral"}},
            {"type": "input_text", "text": instruction, "cache_control": {"type": "ephemeral"}},
        ]
        for segment in context_segments:
            content.append(
                {
                    "type": "input_text",
                    "text": f"Context entry (older to newer): {{{segment}}}",
                    "cache_control": {"type": "ephemeral"},
                }
            )
        content.append({"type": "input_text", "text": f"Subtitle to translate: {{{subtitle_text}}}"})

        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": [content[0]]},
                {"role": "user", "content": content[1:]},
            ],
            "max_output_tokens": 1000,
            "temperature": temperature,
        }
        response = self._request_with_retry(responses_url, payload)
        output = response.get("output")
        if not isinstance(output, list):
            # Fall back to chat endpoint.
            return None
        for entry in output:
            if not isinstance(entry, dict):
                continue
            for part in entry.get("content", []):
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if text:
                        return str(text)
                elif isinstance(part, str):
                    return part
        return None
