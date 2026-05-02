from typing import List, Tuple

def format_vote_message(rule_text: str, yes_list: List[Tuple[int, str, str]], no_list: List[Tuple[int, str, str]], yes_count: int, no_count: int, needed: int, vote_id: int) -> str:
    # yes_list and no_list rows are (user_id, username, display_name)
    def name(u):
        user_id, username, display_name = u
        if username:
            return f"@{username}"
        return display_name or str(user_id)

    yes_display = ", ".join(name(u) for u in yes_list)
    no_display = ", ".join(name(u) for u in no_list)

    if len(yes_display) == 0:
        yes_display = "—"
    if len(no_display) == 0:
        no_display = "—"

    text = (
        f"📢 Правило:\n{rule_text}\n\n"
        f"✅ За ({yes_count}): {yes_display}\n"
        f"❌ Против ({no_count}): {no_display}\n\n"
        f"Требуется для принятия: более 50% участников (минимум {needed} "
        f"из общего числа).\n"
        f"(админы: /close_vote {vote_id})"
    )
    return text
