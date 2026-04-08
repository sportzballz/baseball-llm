import os

from openai import OpenAI


def get_pick_summary(context, fallback_commentary, model_name):
    """
    Send today's picks to an LLM and get back a summary with a pick-of-the-day suggestion.

    Args:
        predictions: list of Prediction objects (already filtered to valid picks)
        model_name: name of the model that generated the picks (e.g. 'ashburn')

    Returns:
        str: LLM-generated summary and pick-of-the-day suggestion
    """
    if not context:
        return fallback_commentary or "No valid pick context."

    style = context.get("style", "beat writer notebook")
    system_prompt = (
        f"You are an expert MLB baseball analyst with this style: '{style}'. You are given a set of model-generated "
        f"picks for today's games produced by the '{model_name}' prediction model. "
        f"Each pick includes the predicted winner, moneyline odds, model confidence "
        f"(0-1 scale, higher is better), data points (winner points / total points), "
        f"starting pitchers, and game time.  Pay attention to weather if relevant and line movement.  Look for over over advantages and underdog picks.\n\n"
    )

    user_prompt = f"Take this commentary '{fallback_commentary}' and make it better based on all the relevent context in this json '{str(context)}'\n\n"

    def _deterministic_fallback_summary():
        return fallback_commentary or "Commentary unavailable."

    def _call_openai(api_key, llm_model, base_url=None):
        client = (
            OpenAI(api_key=api_key, base_url=base_url)
            if base_url
            else OpenAI(api_key=api_key)
        )
        response = client.chat.completions.create(
            model=llm_model,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    errors = []

    # Primary: OpenAI direct
    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_model = os.environ.get("OPENAI_SUMMARY_MODEL", "gpt-4o-mini")
    if openai_key:
        try:
            summary = _call_openai(openai_key, openai_model)
            print(f"LLM summary provider=openai model={openai_model}")
            return summary
        except Exception as e:
            errors.append(f"openai:{e}")

    # Fallback provider: OpenRouter (OpenAI-compatible API)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    openrouter_model = os.environ.get("OPENROUTER_SUMMARY_MODEL", "openai/gpt-4o-mini")
    if openrouter_key:
        try:
            summary = _call_openai(
                openrouter_key,
                openrouter_model,
                base_url="https://openrouter.ai/api/v1",
            )
            print(f"LLM summary provider=openrouter model={openrouter_model}")
            return summary
        except Exception as e:
            errors.append(f"openrouter:{e}")

    if errors:
        print(
            "LLM summary provider fallback -> deterministic; errors: "
            + " | ".join(errors)
        )
    return _deterministic_fallback_summary()


def get_pick_summaries(predictions, model_name):
    """
    Send today's picks to an LLM and get back a summary with a pick-of-the-day suggestion.

    Args:
        predictions: list of Prediction objects (already filtered to valid picks)
        model_name: name of the model that generated the picks (e.g. 'ashburn')

    Returns:
        str: LLM-generated summary and pick-of-the-day suggestion
    """
    if not predictions:
        return "No valid picks today."

    picks_text = "\n".join(
        f"- {p.winning_team} over {p.losing_team} | "
        f"Odds: {p.odds} | Confidence: {p.confidence} | "
        f"Data Points: {p.data_points} | "
        f"Pitchers: {p.winning_pitcher} vs {p.losing_pitcher} | "
        f"Game Time: {p.gameTime}{p.ampm}"
        for p in predictions
        if p.winning_team != "-"
    )

    if not picks_text:
        return "No valid picks today."

    system_prompt = (
        f"You are an expert MLB baseball analyst. You are given a set of model-generated "
        f"picks for today's games produced by the '{model_name}' prediction model. "
        f"Each pick includes the predicted winner, moneyline odds, model confidence "
        f"(0-1 scale, higher is better), data points (winner points / total points), "
        f"starting pitchers, and game time.\n\n"
        f"Provide:\n"
        f"1. A brief summary of all today's picks\n"
        f"2. Your PICK OF THE DAY — the single best bet with a short explanation of why "
        f"it stands out (consider confidence, odds value, and pitching matchup)\n"
        f"3. Any picks to avoid or that look risky\n\n"
        f"Keep the response concise and suitable for posting in a Slack channel."
    )

    user_prompt = (
        f"Here are today's picks from the {model_name} model:\n\n{picks_text}\n\n"
        f"What's your summary and pick of the day?"
    )

    def _deterministic_fallback_summary():
        valid = [p for p in predictions if p.winning_team != "-"]
        if not valid:
            return "No valid picks today."

        by_conf = sorted(valid, key=lambda p: float(p.confidence), reverse=True)
        pick = by_conf[0]
        lines = [
            f"Summary: {len(valid)} qualifying picks generated by {model_name}.",
            (
                f"Pick of the Day: {pick.winning_team} over {pick.losing_team} "
                f"({pick.odds}) — confidence {pick.confidence}, data points {pick.data_points}, "
                f"pitching {pick.winning_pitcher} vs {pick.losing_pitcher}."
            ),
        ]

        risky = [p for p in valid if float(p.confidence) < 0.10]
        if risky:
            risky_text = ", ".join(
                [f"{p.winning_team} over {p.losing_team}" for p in risky[:3]]
            )
            lines.append(f"Risk watch: lower-confidence leans include {risky_text}.")
        else:
            lines.append("Risk watch: no ultra-low-confidence plays flagged.")
        return "\n".join(lines)

    def _call_openai(api_key, llm_model, base_url=None):
        client = (
            OpenAI(api_key=api_key, base_url=base_url)
            if base_url
            else OpenAI(api_key=api_key)
        )
        response = client.chat.completions.create(
            model=llm_model,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    errors = []

    # Primary: OpenAI direct
    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_model = os.environ.get("OPENAI_SUMMARY_MODEL", "gpt-4o-mini")
    if openai_key:
        try:
            summary = _call_openai(openai_key, openai_model)
            print(f"LLM summary provider=openai model={openai_model}")
            return summary
        except Exception as e:
            errors.append(f"openai:{e}")

    # Fallback provider: OpenRouter (OpenAI-compatible API)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    openrouter_model = os.environ.get("OPENROUTER_SUMMARY_MODEL", "openai/gpt-4o-mini")
    if openrouter_key:
        try:
            summary = _call_openai(
                openrouter_key,
                openrouter_model,
                base_url="https://openrouter.ai/api/v1",
            )
            print(f"LLM summary provider=openrouter model={openrouter_model}")
            return summary
        except Exception as e:
            errors.append(f"openrouter:{e}")

    if errors:
        print(
            "LLM summary provider fallback -> deterministic; errors: "
            + " | ".join(errors)
        )
    return _deterministic_fallback_summary()


def massage_commentary(commentary_text, context):
    """
    Rewrite a single pick commentary block for readability while preserving meaning.

    Args:
        commentary_text: original commentary text
        context: dict with pick context (winner/loser/odds/etc)

    Returns:
        str: improved commentary text (or original text on failure)
    """
    original = (commentary_text or "").strip()
    if not original:
        return original

    system_prompt = (
        "You are an expert MLB betting editor. Rewrite commentary for clarity and flow while preserving facts, "
        "numbers, and intent. Keep it concise, natural, and publication-ready. Do not invent new facts."
    )

    user_prompt = (
        f"Context JSON: {str(context)}\n\n"
        f"Original commentary:\n{original}\n\n"
        "Rewrite this commentary in one polished paragraph."
    )

    def _call_openai(api_key, llm_model, base_url=None):
        client = (
            OpenAI(api_key=api_key, base_url=base_url)
            if base_url
            else OpenAI(api_key=api_key)
        )
        response = client.chat.completions.create(
            model=llm_model,
            temperature=0.4,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    errors = []

    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_model = os.environ.get("OPENAI_COMMENTARY_MODEL", "gpt-4o-mini")
    if openai_key:
        try:
            out = _call_openai(openai_key, openai_model)
            if out and str(out).strip():
                return str(out).strip()
        except Exception as e:
            errors.append(f"openai:{e}")

    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    openrouter_model = os.environ.get(
        "OPENROUTER_COMMENTARY_MODEL", "openai/gpt-4o-mini"
    )
    if openrouter_key:
        try:
            out = _call_openai(
                openrouter_key,
                openrouter_model,
                base_url="https://openrouter.ai/api/v1",
            )
            if out and str(out).strip():
                return str(out).strip()
        except Exception as e:
            errors.append(f"openrouter:{e}")

    if errors:
        print("Commentary massage fallback -> original; errors: " + " | ".join(errors))
    return original
