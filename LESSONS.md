# Development Lessons

This file documents important lessons learned during development to help avoid repeating the same mistakes and share knowledge.

## Claude API Tool Calling

**Date:** February 26, 2025

**Problem:** When implementing the `claude_tools.py` script, we encountered several challenges with the Claude API's tool calling format:

1. The tool_use_id field must match exactly between the tool use request and tool result
2. The API has specific format requirements for the messages array that aren't immediately obvious
3. Proper structuring of the content arrays is critical

**Solution:**

We simplified the approach to focus on the initial tool call request instead of trying to implement the full conversation flow. The working approach:

```python
# Initial prompt to get Claude to use the tool
response = client.messages.create(
    model=model,
    max_tokens=1024,
    tools=[weather_tool],
    messages=[
        {"role": "user", "content": f"What's the weather like in {location}? Please use {unit} units."}
    ]
)
```

For a complete implementation, the messages array needs to follow this exact structure:

```python
messages = [
    {"role": "user", "content": "What's the weather like in San Francisco?"},
    {"role": "assistant", "content": [
        {"type": "tool_use", "name": "get_weather", "id": "tool_1", "input": {"location": "San Francisco, CA", "unit": "celsius"}}
    ]},
    {"role": "user", "content": [
        {"type": "tool_result", "tool_result": {"tool_use_id": "tool_1", "content": "Weather data here"}}
    ]}
]
```

**Key takeaways:**

1. Reference the exact format in the [Anthropic API docs](https://docs.anthropic.com/claude/reference/tool-use)
2. Always ensure the `tool_use_id` in the tool result matches the `id` in the original tool use
3. For debugging tool calls, start with the simplest possible implementation
4. Use a consistent structure for tool messages
5. When errors occur, check the format of your messages array carefully
