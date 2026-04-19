from __future__ import annotations

from typing import Any


def tool_calls(trace: dict[str, Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for message in trace.get("messages", []):
        if message.get("role") == "assistant":
            for call in message.get("tool_calls", []):
                calls.append(call)
    return calls


def tool_names(trace: dict[str, Any]) -> list[str]:
    return [call.get("name", "") for call in tool_calls(trace)]


def fetched_urls(trace: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for call in tool_calls(trace):
        if call.get("name") == "fetch_url":
            args = call.get("args", {})
            if isinstance(args, dict) and "url" in args:
                urls.append(str(args["url"]))
    return urls


def fetched_texts(trace: dict[str, Any]) -> dict[str, str]:
    outputs: dict[str, str] = {}
    pending_urls = fetched_urls(trace)
    url_index = 0
    for message in trace.get("messages", []):
        if message.get("role") != "tool" or message.get("name") != "fetch_url":
            continue
        if url_index >= len(pending_urls):
            break
        content = message.get("content")
        if isinstance(content, str):
            outputs[pending_urls[url_index]] = content
        url_index += 1
    return outputs


def final_answer(trace: dict[str, Any]) -> str:
    return str(trace.get("final_answer") or "")

