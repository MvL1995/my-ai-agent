def normalize_user_input(raw_input):
    cleaned_input = raw_input.strip()

    if not cleaned_input:
        return None

    return cleaned_input