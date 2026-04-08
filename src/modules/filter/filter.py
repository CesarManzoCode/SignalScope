def filter_items(items, config):
    technologies = config.get("technologies", [])

    if not technologies:
        return items

    filtered = []

    for item in items:
        text = (item.title + " " + item.summary).lower()

        if any(tech.lower() in text for tech in technologies):
            filtered.append(item)

    return filtered