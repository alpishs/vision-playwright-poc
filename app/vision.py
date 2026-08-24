import json
import re

import ollama


MODEL_NAME = "qwen2.5vl:7b"


def extract_json(content: str) -> dict:
    """
    Extract a JSON object from the Vision AI response.

    Handles:
    - Pure JSON
    - ```json ... ```
    - ``` ... ```
    - Text surrounding JSON
    """

    if not content:
        raise ValueError(
            "Vision AI returned an empty response."
        )

    content = content.strip()

    # --------------------------------
    # Remove markdown code fences
    # --------------------------------

    content = re.sub(
        r"^```(?:json)?\s*",
        "",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"\s*```$",
        "",
        content,
    )

    content = content.strip()

    # --------------------------------
    # Try direct JSON parsing
    # --------------------------------

    try:
        result = json.loads(content)

        if not isinstance(result, dict):
            raise ValueError(
                "Vision AI returned JSON, "
                "but it is not a JSON object."
            )

        return result

    except json.JSONDecodeError:
        pass

    # --------------------------------
    # Find JSON object inside response
    # --------------------------------

    match = re.search(
        r"\{.*\}",
        content,
        re.DOTALL,
    )

    if match:

        json_content = match.group(0)

        try:

            result = json.loads(
                json_content
            )

            if not isinstance(result, dict):

                raise ValueError(
                    "Extracted JSON is not "
                    "a JSON object."
                )

            return result

        except json.JSONDecodeError:
            pass

    # --------------------------------
    # Nothing worked
    # --------------------------------

    raise ValueError(
        "Vision AI did not return valid JSON.\n\n"
        f"Raw response:\n{content}"
    )


def generate_action_plan(
    image_path: str,
    elements: list,
    goal: str,
) -> dict:

    """
    Ask Vision AI to understand the UI and
    generate a Playwright action plan.
    """

    # --------------------------------
    # Build DOM element description
    # --------------------------------

    elements_text = "\n".join(
        [
            f"""
Element {index}:
selector: {element.get("selector")}
tag: {element.get("tag")}
text: {element.get("text")}
placeholder: {element.get("placeholder")}
type: {element.get("type")}
ariaLabel: {element.get("ariaLabel")}
"""
            for index, element in enumerate(
                elements,
                start=1,
            )
        ]
    )

    # --------------------------------
    # Prompt
    # --------------------------------

    prompt = f"""
You are a browser automation agent.

Analyze the screenshot and the available
DOM elements.

USER GOAL:

{goal}


AVAILABLE DOM ELEMENTS:

{elements_text}


Create a browser action plan.

IMPORTANT:

Return ONLY a JSON object.

Do NOT use markdown.

Do NOT use ```json.

Do NOT provide explanations.

Do NOT write anything before or after
the JSON object.


The JSON MUST follow this structure:

{{
  "actions": [
    {{
      "target": "Username input",
      "selector": "#username",
      "action": "fill",
      "value": "{{USERNAME}}"
    }},
    {{
      "target": "Password input",
      "selector": "#password",
      "action": "fill",
      "value": "{{PASSWORD}}"
    }},
    {{
      "target": "Sign In button",
      "selector": "#login-button",
      "action": "click"
    }}
  ]
}}


RULES:

1. Use ONLY elements from the
   AVAILABLE DOM ELEMENTS.

2. selector MUST correspond to one of
   the provided DOM elements.

3. Use the screenshot to understand
   the visual meaning of the elements.

4. Supported actions are ONLY:

   - fill
   - click

5. Use {{USERNAME}} for username values.

6. Use {{PASSWORD}} for password values.

7. NEVER invent a selector.

8. NEVER include actual passwords.

9. Return ONLY valid JSON.
"""

    print(
        "\n📤 Sending request to Vision AI..."
    )

    # --------------------------------
    # Call Ollama
    # --------------------------------

    response = ollama.chat(
        model=MODEL_NAME,
        options={
            "temperature": 0,
        },
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [image_path],
            }
        ],
    )

    # --------------------------------
    # Get response
    # --------------------------------

    content = response["message"]["content"]

    print(
        "\n🤖 Raw Vision AI response:"
    )

    print(
        "--------------------------------"
    )

    print(content)

    print(
        "--------------------------------"
    )

    # --------------------------------
    # Validate response
    # --------------------------------

    if not content or not content.strip():

        raise ValueError(
            "Vision AI returned an empty response."
        )

    # --------------------------------
    # Parse JSON
    # --------------------------------

    result = extract_json(content)

    # --------------------------------
    # Validate action plan
    # --------------------------------

    if "actions" not in result:

        raise ValueError(
            "Vision AI response does not "
            "contain an 'actions' field.\n\n"
            f"Response:\n{result}"
        )

    if not isinstance(
        result["actions"],
        list,
    ):

        raise ValueError(
            "'actions' must be a list."
        )

    # --------------------------------
    # Validate individual actions
    # --------------------------------

    for index, action in enumerate(
        result["actions"],
        start=1,
    ):

        if not isinstance(
            action,
            dict,
        ):

            raise ValueError(
                f"Action {index} is not "
                f"a JSON object."
            )

        if "target" not in action:

            raise ValueError(
                f"Action {index} is missing "
                f"'target'."
            )

        if "action" not in action:

            raise ValueError(
                f"Action {index} is missing "
                f"'action'."
            )

        if action["action"] not in {
            "fill",
            "click",
        }:

            raise ValueError(
                f"Action {index} has "
                f"unsupported action: "
                f"{action['action']}"
            )

        if action["action"] == "fill":

            if "value" not in action:

                raise ValueError(
                    f"Fill action {index} "
                    f"is missing 'value'."
                )

    print(
        "\n✅ Vision AI action plan "
        "validated."
    )

    return result


def validate_ui_state(
    image_path: str,
    expected_state: str,
) -> dict:

    """
    Ask Vision AI to validate the resulting
    browser UI state.
    """

    # --------------------------------
    # Prompt
    # --------------------------------

    prompt = f"""
You are a UI testing agent.

Analyze the screenshot of the web page.

EXPECTED UI STATE:

{expected_state}


Determine whether the screenshot
matches the expected state.


Return ONLY valid JSON.

Required format:

{{
  "passed": true,
  "state": "success",
  "message": "Login successful!"
}}


RULES:

1. "passed" must be true or false.

2. Identify the visible UI state.

3. Extract the visible result message
   if one exists.

4. Use the screenshot as the source
   of truth for visual validation.

5. Do NOT use markdown.

6. Do NOT provide explanations.

7. Return ONLY JSON.
"""

    print(
        "\n📤 Sending screenshot "
        "to Vision AI for validation..."
    )

    # --------------------------------
    # Call Ollama
    # --------------------------------

    response = ollama.chat(
        model=MODEL_NAME,
        options={
            "temperature": 0,
        },
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [image_path],
            }
        ],
    )

    # --------------------------------
    # Get response
    # --------------------------------

    content = response["message"]["content"]

    print(
        "\n👁️ Raw Vision validation:"
    )

    print(
        "--------------------------------"
    )

    print(content)

    print(
        "--------------------------------"
    )

    if not content or not content.strip():

        raise ValueError(
            "Vision AI returned an empty "
            "validation response."
        )

    # --------------------------------
    # Parse JSON
    # --------------------------------

    result = extract_json(content)

    # --------------------------------
    # Validate response structure
    # --------------------------------

    if "passed" not in result:

        raise ValueError(
            "Vision validation response "
            "is missing 'passed'."
        )

    if not isinstance(
        result["passed"],
        bool,
    ):

        raise ValueError(
            "'passed' must be a boolean."
        )

    if "state" not in result:

        raise ValueError(
            "Vision validation response "
            "is missing 'state'."
        )

    if "message" not in result:

        result["message"] = ""

    print(
        "\n✅ Vision validation "
        "response validated."
    )

    return result