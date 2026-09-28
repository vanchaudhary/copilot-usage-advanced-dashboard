import json


def convert_day(metrics_day):
    # Use the 'date' field in the Metrics API as the 'day' field in the Usage API
    day = metrics_day.get("date")

    # Handle Copilot IDE code completion indicators
    code_completions = metrics_day.get("copilot_ide_code_completions")
    total_suggestions_count = 0
    total_acceptances_count = 0
    total_lines_suggested = 0
    total_lines_accepted = 0

    # breakdown will summarize completion-related metrics by editor and language
    breakdown_dict = {}

    if code_completions:
        editors = code_completions.get("editors", [])
        for editor in editors:
            editor_name = editor.get("name", "unknown")
            for model in editor.get("models", []):
                model_name = model.get("name", "unknown")
                for lang in model.get("languages", []):
                    lang_name = lang.get("name", "unknown")
                    key = (editor_name, model_name, lang_name)
                    if key not in breakdown_dict:
                        breakdown_dict[key] = {
                            "editor": editor_name,
                            "model": model_name,
                            "language": lang_name,
                            "suggestions_count": 0,
                            "acceptances_count": 0,
                            "lines_suggested": 0,
                            "lines_accepted": 0,
                            "active_users": lang.get("total_engaged_users", 0),
                        }
                    breakdown_dict[key]["suggestions_count"] += lang.get(
                        "total_code_suggestions", 0
                    )
                    breakdown_dict[key]["acceptances_count"] += lang.get(
                        "total_code_acceptances", 0
                    )
                    breakdown_dict[key]["lines_suggested"] += lang.get(
                        "total_code_lines_suggested", 0
                    )
                    breakdown_dict[key]["lines_accepted"] += lang.get(
                        "total_code_lines_accepted", 0
                    )

                    total_suggestions_count += lang.get("total_code_suggestions", 0)
                    total_acceptances_count += lang.get("total_code_acceptances", 0)
                    total_lines_suggested += lang.get("total_code_lines_suggested", 0)
                    total_lines_accepted += lang.get("total_code_lines_accepted", 0)

    breakdown_list = list(breakdown_dict.values())

    # Handle Copilot IDE chat indicators
    chat = metrics_day.get("copilot_ide_chat")
    total_chat_acceptances = 0
    total_chat_turns = 0
    total_active_chat_users = 0
    total_chat_copy_events = 0
    total_chat_insertion_events = 0

    breakdown_chat_dict = {}

    if chat:
        total_active_chat_users = chat.get("total_engaged_users", 0)
        for editor in chat.get("editors", []):
            editor_name = editor.get("name", "unknown")
            for model in editor.get("models", []):
                model_name = model.get("name", "unknown")
                key = (editor_name, model_name)
                if key not in breakdown_chat_dict:
                    breakdown_chat_dict[key] = {
                        "editor": editor_name,
                        "model": model_name,
                        "chat_turns": 0,
                        "chat_copy_events": 0,
                        "chat_insertion_events": 0,
                        "chat_acceptances": 0,
                        "active_users": model.get("total_engaged_users", 0),
                    }
                total_chat_copy_events += model.get("total_chat_copy_events", 0)
                total_chat_insertion_events += model.get(
                    "total_chat_insertion_events", 0
                )
                total_chat_acceptances += model.get(
                    "total_chat_insertion_events", 0
                ) + model.get("total_chat_copy_events", 0)
                total_chat_turns += model.get("total_chats", 0)
                breakdown_chat_dict[key]["chat_turns"] += model.get("total_chats", 0)
                breakdown_chat_dict[key]["chat_copy_events"] += model.get(
                    "total_chat_copy_events", 0
                )
                breakdown_chat_dict[key]["chat_insertion_events"] += model.get(
                    "total_chat_insertion_events", 0
                )
                breakdown_chat_dict[key]["chat_acceptances"] += model.get(
                    "total_chat_insertion_events", 0
                ) + model.get("total_chat_copy_events", 0)

    breakdown_chat_list = list(breakdown_chat_dict.values())

    usage = {
        "day": day,
        "total_suggestions_count": total_suggestions_count,
        "total_acceptances_count": total_acceptances_count,
        "total_lines_suggested": total_lines_suggested,
        "total_lines_accepted": total_lines_accepted,
        "total_active_users": metrics_day.get("total_active_users", 0),
        "total_chat_acceptances": total_chat_acceptances,
        "total_chat_turns": total_chat_turns,
        "total_active_chat_users": total_active_chat_users,
        "total_chat_copy_events": total_chat_copy_events,
        "total_chat_insertion_events": total_chat_insertion_events,
        "breakdown": breakdown_list,
        "breakdown_chat": breakdown_chat_list,
    }
    return usage


def convert_metrics_to_usage(metrics):
    # metrics is a list, each element is the indicator data for one day
    return [convert_day(day) for day in metrics]


def convert_user_report_to_usage(records):
    grouped = {}
    for record in records:
        day = record.get("day")
        if not day or not record.get("user_login"):
            continue
        team = record.get("team_slug") or "no-team"
        entry = grouped.setdefault((team, day), {
            "day": day,
            "total_suggestions_count": 0,
            "total_acceptances_count": 0,
            "total_lines_suggested": 0,
            "total_lines_accepted": 0,
            "total_active_users": 0,
            "total_chat_acceptances": 0,
            "total_chat_turns": 0,
            "total_active_chat_users": 0,
            "total_chat_copy_events": 0,
            "total_chat_insertion_events": 0,
            "breakdown": [],
            "breakdown_chat": [],
        })
        entry["report_source"] = "user-28-day"
        entry["total_active_users"] += 1
        entry["total_suggestions_count"] += record.get("code_generation_activity_count") or 0
        entry["total_acceptances_count"] += record.get("code_acceptance_activity_count") or 0
        entry["total_lines_suggested"] += record.get("loc_suggested_to_add_sum") or 0
        entry["total_lines_accepted"] += record.get("loc_added_sum") or 0
        entry["total_active_chat_users"] += int(bool(record.get("used_chat")))

        for item in record.get("totals_by_language_model") or []:
            entry["breakdown"].append({
                "report_dimension": "language_model",
                "language": item.get("language") or "unknown",
                "model": item.get("model") or "unknown",
                "editor": "all",
                "suggestions_count": item.get("code_generation_activity_count") or 0,
                "acceptances_count": item.get("code_acceptance_activity_count") or 0,
                "lines_suggested": item.get("loc_suggested_to_add_sum") or 0,
                "lines_accepted": item.get("loc_added_sum") or 0,
                "active_users": 1,
            })
        for item in record.get("totals_by_ide") or []:
            entry["breakdown"].append({
                "report_dimension": "ide",
                "language": "all", "model": "all", "editor": item.get("ide") or "unknown",
                "suggestions_count": item.get("code_generation_activity_count") or 0,
                "acceptances_count": item.get("code_acceptance_activity_count") or 0,
                "lines_suggested": item.get("loc_suggested_to_add_sum") or 0,
                "lines_accepted": item.get("loc_added_sum") or 0,
                "active_users": 1,
            })
        for item in record.get("totals_by_model_feature") or []:
            if "chat" not in (item.get("feature") or ""):
                continue
            interactions = item.get("user_initiated_interaction_count") or 0
            entry["total_chat_turns"] += interactions
            entry["total_chat_acceptances"] += item.get("code_acceptance_activity_count") or 0
            entry["breakdown_chat"].append({
                "report_source": "user-28-day",
                "editor": "all", "model": item.get("model") or "unknown",
                "chat_turns": interactions,
                "chat_copy_events": 0,
                "chat_insertion_events": 0,
                "chat_acceptances": item.get("code_acceptance_activity_count") or 0,
                "active_users": 1,
            })
    result = {}
    for (team, _), entry in grouped.items():
        for field, dimensions, values in (
            ("breakdown", ("language", "model", "editor"), ("suggestions_count", "acceptances_count", "lines_suggested", "lines_accepted", "active_users")),
            ("breakdown_chat", ("editor", "model"), ("chat_turns", "chat_copy_events", "chat_insertion_events", "chat_acceptances", "active_users")),
        ):
            buckets = {}
            for item in entry[field]:
                key = tuple(item[dimension] for dimension in dimensions)
                if key not in buckets:
                    buckets[key] = item.copy()
                else:
                    for value in values:
                        buckets[key][value] += item[value]
            entry[field] = list(buckets.values())
        result.setdefault(team, []).append(entry)
    return result


def main():
    # if len(sys.argv) < 3:
    #     print("Usage: python conversion.py input.json output.json")
    #     sys.exit(1)
    input_file = "logs/2025-02-22/nekoaru_level1-team1_copilot_metrics_2025-02-22.json"  # sys.argv[1]
    output_file = "tmp/output.json"  # sys.argv[2]

    with open(input_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    usage = convert_metrics_to_usage(metrics)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(usage, f, indent=2)


if __name__ == "__main__":
    main()
