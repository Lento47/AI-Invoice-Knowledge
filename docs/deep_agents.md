# Deep agents for the invoice platform

The project now ships with a helper that wires [LangGraph deep agents](https://github.com/langchain-ai/deepagents)
into our domain specific tools. Deep agents combine long-horizon planning, a
virtual file system, and optional sub agents so the LLM can break down more
complex operations than a standard ReAct loop.

## Why it helps

* **Task decomposition** – Agents write to a to-do list before acting, which
  keeps multi-step invoice reviews on track.
* **Scratch space** – The virtual file system lets the model save structured
  extraction results, intermediate calculations, or quick notes for later
  steps.
* **Context isolation** – Built-in sub agents can tackle focused jobs (for
  example, a critique step) without polluting the main conversation context.
* **Human approval** – Deep agents understand LangGraph's human-in-the-loop
  middleware, allowing operators to pause and approve sensitive tool calls like
  payment forecasts.

## Configuration

The Python package dependency is declared in `pyproject.toml`. Set the model
identifier the agent should use via configuration. You can either persist the
value through the admin API or define an environment variable:

```bash
export AGENT_MODEL="openai:gpt-4o-mini"
```

This model string is forwarded directly to `deepagents.create_deep_agent`, so
you can use any LangChain-compatible chat model (OpenAI, Anthropic, Azure, or
Ollama via `langchain-ollama`).

## Using the helper

The helper lives in `ai_invoice.agents`. It exposes the default instructions and
a factory for building a deep agent that understands the invoice toolchain.

```python
from ai_invoice.agents import create_invoice_deep_agent

agent = create_invoice_deep_agent()
response = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Summarise the totals in invoice1.txt and predict when it will be paid.",
            }
        ],
        # Optional: provide files the agent can read/write
        "files": {
            "invoice1.txt": open("data/samples/invoice1.txt", "r", encoding="utf-8").read(),
        },
    }
)

print(response["messages"][-1]["content"])
```

Three tools are registered by default:

| Tool | Purpose |
| --- | --- |
| `parse_invoice_text` | Convert OCR text into a structured invoice payload. |
| `classify_invoice_text` | Run the in-house document classifier on arbitrary invoice text. |
| `predict_invoice_payment` | Forecast payment timing when supplied with the six predictive features. |

Pass `extra_tools=` to expose additional LangChain tools and `instructions=` to
append operator specific guidance. Any keyword arguments supported by
`deepagents.create_deep_agent` (such as custom sub agents or middleware) are
forwarded untouched.

For more ideas, review the upstream [`deepagents` README](https://github.com/langchain-ai/deepagents)
and the example research agent shipped with that project.

