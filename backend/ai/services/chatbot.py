"""
Chatbot service layer.

Connects the AI assistant to the Groq API (official groq SDK) using
controlled, tenant-scoped function calling.

Security model:
  - All Groq calls happen server-side only.
  - The API key comes from settings (GROQ_API_KEY env var), never from
    the client, and is never logged or serialized.
  - Groq has no direct database access. The only data it can read is
    returned by the controlled tools in ``tools.py``, and every one of
    those functions enforces ``organization`` filtering server-side. The
    organization is injected from the authenticated user, never from the
    model, so cross-tenant access is impossible.
"""

import logging
import json
import re

from django.conf import settings

from .tools import TOOL_DECLARATIONS, dispatch_tool

logger = logging.getLogger(__name__)

# Friendly, user-facing messages for each failure class. The raw exception
# is still logged server-side so developers do not lose debugging detail.
ERROR_HTTP_STATUS = {
    "rate_limit": 429,
    "ai_error": 500,
    "ai_config": 503,
    "model_unavailable": 503,
    "server": 502,
    "network": 502,
    "timeout": 504,
    "internal": 500,
}

# Bounds for client-supplied conversation history. History is only used
# to give the model lightweight conversational context; it never controls
# tool execution or tenancy. These guards keep payloads small and safe.
MAX_HISTORY_TURNS = 8
MAX_MESSAGE_CHARS = 2000


class AssistantError(Exception):
    """Typed chat failure with a machine-readable code and friendly message."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message

SYSTEM_INSTRUCTION = (
    "You are the AI Chat assistant for INVENTO, a smart multi-tenant "
    "inventory management system. You answer questions about "
    "products, inventory, sales, purchases, customers, suppliers, "
    "categories, stock movements and overall business performance. "
    "Reply naturally and conversationally to greetings, thanks and simple "
    "chit-chat (e.g. 'hi', 'hello', 'hey', 'thank you', 'bye') WITHOUT "
    "calling any tool. Only call a tool when the user is explicitly asking "
    "about business data or analysis — products, sales, purchases, "
    "inventory, stock, customers, suppliers, reports, performance or "
    "restocking. Never call a tool 'just in case' and never summarise "
    "business data that was not asked for. "
    "You can only answer using the tools provided to you; never invent "
    "numbers. Choose the most appropriate tool for each question, and use "
    "date-window parameters (today, this_week, this_month, last_30_days, "
    "this_year, explicit start_date/end_date) where relevant. "
    "Every tool is already restricted to the current business's own data; "
    "do not ask for other organizations or raw database access. "
    "All monetary values are in Nepalese Rupees (NPR). Always express "
    "money using the 'Rs.' prefix followed by a space and a comma-grouped "
    "number with two decimal places, for example 'Rs. 2,500.00', "
    "'Rs. 52.50', 'Rs. 10,000.00'. Never use '$', 'USD', 'dollars', or any "
    "other currency symbol, and never perform or invent any currency "
    "conversion. "
    "Use the tools to gather facts first, then write a concise, helpful, "
    "friendly answer in plain text. If the available data cannot answer a "
    "question accurately, say so plainly instead of guessing."
)


# Bare conversational utterances (normalised lower-case, punctuation-free)
# that are answered directly and never routed to Groq or the business tools.
# A greeting, thanks, farewell or simple acknowledgment does not need any
# business data and should never trigger a tool call. Everything else falls
# through to the normal Groq function-calling flow.
_GREETINGS = {
    "hi", "hello", "hey", "hi there", "hello there", "hey there",
    "greetings", "howdy", "hiya", "yo", "sup", "whats up",
    "good morning", "good afternoon", "good evening", "good day",
}
_THANKS = {
    "thanks", "thank you", "thank u", "thx", "ty", "thankyou",
    "thanks a lot", "thank you very much", "cheers",
}
_FAREWELLS = {
    "bye", "bye bye", "goodbye", "good night", "goodnight",
    "see you", "see you later", "see ya", "cya", "take care",
}
_ACKNOWLEDGEMENTS = {
    "ok", "okay", "sure", "fine", "alright", "alrighty",
    "got it", "gotcha", "yes", "yep", "yeah", "no", "nope",
}

_GREETING_REPLIES = {
    "hi": "Hi! How can I help you today?",
    "hello": "Hello! What can I help you with?",
    "hey": "Hey! How can I help?",
    "hi there": "Hi there! How can I help you today?",
    "hello there": "Hello there! What can I help you with?",
    "hey there": "Hey there! How can I help?",
    "greetings": "Greetings! How can I help you today?",
    "howdy": "Howdy! How can I help?",
    "hiya": "Hiya! How can I help you today?",
    "yo": "Hey! How can I help?",
    "sup": "Hey! How can I help?",
    "whats up": "Hey! How can I help?",
}

_CONVERSATIONAL_MAX_CHARS = 30


def _normalize_conversational(text):
    """Lower-case, strip punctuation/emoji and collapse whitespace."""
    cleaned = re.sub(r"[^a-z]+", " ", str(text or "").lower())
    return " ".join(cleaned.split())


def _conversational_reply(message):
    """Return a natural conversational reply for bare chit-chat, else None.

    Only whole-message conversational text is matched (bounded in length),
    so messages that embed a business request always fall through to the
    Groq function-calling flow.
    """
    normalized = _normalize_conversational(message)
    if not normalized or len(normalized) > _CONVERSATIONAL_MAX_CHARS:
        return None

    if normalized in _GREETINGS:
        if normalized.startswith("good "):
            return normalized.capitalize() + "! How can I help you today?"
        return _GREETING_REPLIES.get(normalized, "Hi! How can I help you today?")
    if normalized in _THANKS:
        return "You're welcome! Let me know if you need anything."
    if normalized in _FAREWELLS:
        return "Goodbye! Feel free to come back whenever you need anything."
    if normalized in _ACKNOWLEDGEMENTS:
        return "Sure! Let me know what you'd like to check."
    return None


def _parse_args(arguments):
    """Convert a Groq tool-call ``arguments`` field into a plain dict.

    Groq hands tool arguments back as a JSON string; guard against
    malformed payloads gracefully. The ``organization`` key is always the
    backend's job, so any model-supplied value is stripped (defense in
    depth: ``dispatch_tool`` also overrides it server-side).
    """
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        args = arguments
    elif isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except (ValueError, TypeError):
            return {}
        args = parsed if isinstance(parsed, dict) else {}
    else:
        args = {}
    args.pop("organization", None)
    return args


def _sanitize_history(history):
    """Convert client-supplied history into a small, safe role/content list.

    Only user/assistant text turns are accepted; system, tool and error
    content, malformed entries, non-string content and any extra fields
    (e.g. a forged ``organization``) are dropped. The list is bounded in
    both turn count and per-message length.

    This is purely conversational context for the model. It never touches
    tenancy or tool execution, which are always driven server-side.
    """
    if not isinstance(history, list):
        return []
    cleaned = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in ("user", "assistant"):
            continue
        if not isinstance(content, str):
            continue
        text = content.strip()[:MAX_MESSAGE_CHARS]
        if not text:
            continue
        cleaned.append({"role": role, "content": text})
    return cleaned[-MAX_HISTORY_TURNS:]


def _build_tool_objects():
    """Build Groq tool objects (OpenAI-compatible schema) from the controlled declarations.

    The declarations only describe the tools; execution always goes through
    ``dispatch_tool`` server-side.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": decl["name"],
                "description": decl["description"],
                "parameters": decl["parameters"],
            },
        }
        for decl in TOOL_DECLARATIONS
    ]


def _get_client(api_key):
    """Create the Groq client (seam for testing).

    An explicit timeout bounds the external AI call so a slow or
    unreachable provider cannot hang the request for the SDK's long
    default (read timeout ~600s). A raised ``APITimeoutError`` is mapped
    by ``_to_assistant_error`` to a friendly 504 response.
    """
    from groq import Groq

    timeout = getattr(settings, "GROQ_TIMEOUT_SECONDS", None)
    if timeout:
        return Groq(api_key=api_key, timeout=timeout)
    return Groq(api_key=api_key)


def _to_assistant_error(exc):
    """
    Map an exception raised by the Groq SDK / HTTP layer to an
    AssistantError with a code and a friendly, user-safe message.

    The raw exception never leaks to the frontend (it is only logged), which
    keeps responses clean and free of any API key material.
    """
    import httpx

    if isinstance(exc, AssistantError):
        return exc

    try:
        from groq import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            InternalServerError,
            NotFoundError,
            PermissionDeniedError,
            RateLimitError,
        )
    except ImportError:  # groq SDK missing entirely
        return AssistantError(
            "internal",
            "Something went wrong while processing your request. Please try again.",
        )

    if isinstance(exc, RateLimitError):
        return AssistantError(
            "rate_limit",
            "The AI assistant is temporarily busy. Please try again in a moment.",
        )

    if isinstance(exc, AuthenticationError):
        return AssistantError(
            "ai_config",
            "The AI service is not configured on this server yet. "
            "Please contact an administrator.",
        )

    if isinstance(exc, PermissionDeniedError):
        return AssistantError(
            "ai_config",
            "The AI service is not configured on this server yet. "
            "Please contact an administrator.",
        )

    if isinstance(exc, BadRequestError):
        # Typically a malformed request (e.g. malformed tool call). Keep it user-friendly.
        return AssistantError(
            "ai_error",
            "The AI assistant could not understand that request. "
            "Please try again in a moment.",
        )

    if isinstance(exc, InternalServerError):
        return AssistantError(
            "server",
            "The AI service is having issues right now. Please try again later.",
        )

    if isinstance(exc, NotFoundError):
        # Typically a requested model that does not exist or was not found.
        return AssistantError(
            "model_unavailable",
            "The AI model for the assistant is temporarily unavailable. "
            "Please try again later.",
        )

    if isinstance(exc, APITimeoutError):
        return AssistantError(
            "timeout",
            "The AI assistant took too long to respond. Please try again.",
        )

    if isinstance(exc, APIConnectionError):
        return AssistantError(
            "network",
            "Could not reach the AI service. Please try again in a moment.",
        )

    if isinstance(exc, httpx.HTTPError):
        return AssistantError(
            "network",
            "Could not reach the AI service. Please try again in a moment.",
        )

    # Anything else: classify by its HTTP status when available.
    status = getattr(exc, "status_code", None)
    if status == 429:
        return AssistantError(
            "rate_limit",
            "The AI assistant is temporarily busy. Please try again in a moment.",
        )
    if status in (401, 403):
        return AssistantError(
            "ai_config",
            "The AI service is not configured on this server yet. "
            "Please contact an administrator.",
        )
    if status == 404:
        return AssistantError(
            "model_unavailable",
            "The AI model for the assistant is temporarily unavailable. "
            "Please try again later.",
        )
    if status is not None and 400 <= status < 500:
        return AssistantError(
            "ai_error",
            "The AI assistant could not understand that request. "
            "Please try again in a moment.",
        )
    if status is not None and status >= 500:
        return AssistantError(
            "server",
            "The AI service is having issues right now. Please try again later.",
        )

    return AssistantError(
        "internal",
        "Something went wrong while processing your request. Please try again.",
    )


def run_assistant(user_message, user, organization, history=None):
    """
    Send a user message to Groq and return its text reply.

    Executes a manual function-calling loop: when the model requests one of
    the controlled tools, the backend runs it (org-scoped) and feeds the
    result back, repeating until the model produces a final text answer.

    ``history`` (optional) is a small sanitised list of previous
    user/assistant turns used only for conversational context.
    """
    api_key = getattr(settings, "GROQ_API_KEY", "")
    model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    max_rounds = getattr(settings, "GROQ_MAX_TOOL_ROUNDS", 4)

    if not api_key:
        logger.warning("Groq chat requested but GROQ_API_KEY is not set.")
        raise AssistantError(
            "ai_config",
            "The AI service is not configured on this server yet. "
            "Please contact an administrator.",
        )

    conversational = _conversational_reply(user_message)
    if conversational:
        return conversational

    try:
        client = _get_client(api_key)

        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
        ]
        messages.extend(_sanitize_history(history))
        messages.append(
            {"role": "user", "content": user_message}
        )
        tools = _build_tool_objects()

        for _ in range(max_rounds):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                temperature=0.2,
            )

            if not response.choices:
                break

            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)

            if not tool_calls:
                text = (message.content or "").strip()
                return text or "I could not find an answer."

            # Echo the model's tool request back into the conversation so
            # Groq can correlate subsequent tool results by id.
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments or "{}",
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )

            # Execute each requested tool server-side (org-scoped).
            for tc in tool_calls:
                result = dispatch_tool(
                    name=tc.function.name,
                    organization=organization,
                    args=_parse_args(tc.function.arguments),
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    }
                )

        return (
            "I could not finish an answer in the allowed number of steps. "
            "Please try a more specific question."
        )

    except Exception as exc:  # noqa: BLE001 - classified into AssistantError
        logger.error(
            "AI chat error (classified=%s): %s",
            type(exc).__name__,
            str(exc)[:500],
        )
        raise _to_assistant_error(exc) from exc


def process_user_query(request, message, history=None):
    """
    Prepare permission and organizational scoping for chatbot requests.

    Returns a dict with:
        - `reply`          : the assistant's answer (None on failure)
        - `context_ready`  : whether the request is tenant-scoped
        - `error`          : {"code", "message"} when the assistant failed
        - `http_status`    : recommended HTTP status for failures
    """
    organization = getattr(request.user, "organization", None)
    context_ready = organization is not None

    try:
        reply = run_assistant(
            user_message=message,
            user=request.user,
            organization=organization,
            history=history,
        )
        return {
            "reply": reply,
            "context_ready": context_ready,
        }
    except AssistantError as exc:
        return {
            "reply": None,
            "context_ready": context_ready,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
            "http_status": ERROR_HTTP_STATUS.get(exc.code, 500),
        }
    except Exception as exc:  # noqa: BLE001 - never leak internals to the UI
        logger.exception("Unexpected error while processing AI chat request.")
        return {
            "reply": None,
            "context_ready": context_ready,
            "error": {
                "code": "internal",
                "message": (
                    "Something went wrong while processing your request. "
                    "Please try again."
                ),
            },
            "http_status": 500,
        }