def intermediate_nl_transform(row):
    tokens = row["docstring_tokens"]
    result = ' '.join(tokens)
    result = result[:result.find("<p >")]
    if len(result.split()) < 10:
        return None
    #return result
    result = row["docstring"]
    result = result[:result.find("<p>")]
    return result

def intermediate_pl_transform(row):
    #tokens = row["code_tokens"]
    #return ' '.join([' '.join(token.split()) for token in tokens])
    return row["code"]


def finetune_nl_transform(row):
    text = ""
    title_exists = type(row["issue_title"]) == str and row["issue_title"] not in ["None", "nan", "NaN"]
    body_exists = type(row["issue_body"]) == str and row["issue_body"] not in ["None", "nan", "NaN"]
    if title_exists:
        text += row["issue_title"]
    if body_exists:
        if title_exists:
            if text.strip()[-1] not in [';', '.']:
                text += '.'
            text += '\n'
        text += row["issue_body"]
    tokens = []
    SEPARATED_SYMBOLS = ['.', ',', ':', ';', '`', '"', "'", '(', ')', '[', ']', '{', '}', '?', '!', '*']
    for line in text.splitlines():
        line.replace("n't", "n t")
        line_tokens = line.split()
        if len(line_tokens) > 0:
            if line_tokens[0][0] == '[':
                line_tokens = line_tokens[1:]
            for word in line_tokens:
                if word.startswith("http://") or word.startswith("https://"):
                    continue
                current_word = ""
                last_ch = ""
                for ch in word:
                    if (last_ch in SEPARATED_SYMBOLS) != (ch in SEPARATED_SYMBOLS):
                        if len(current_word) > 0:
                            tokens.append(current_word)
                            current_word = ""
                    current_word += ch
                    last_ch = ch
                if len(current_word) > 0:
                    tokens.append(current_word)
    result = ' '.join(tokens)
    result = result[:-1] if result.endswith(".") else result # simulates result = result[:result.find("<p >")] behavior
    if len(result.split()) < 10:
        return None
    #return result
    result = text
    words = result.split()
    # Remove URLs as usual
    for word in words:
        if word.startswith("http://") or word.startswith("https://"):
            i = result.find(word)
            j = i + len(word)
            result = result[:i] + result[j:]
    return result

def finetune_method_pl_transform(row):
    if row["method_nonempty_lines"] < 3 or row["added_nonempty_lines"] / row["method_nonempty_lines"] < 0.35:
        return None
    #tokens = row["code_tokens"]
    #return ' '.join([' '.join(token.split()) for token in tokens])
    return row["code"]


#import nltk

def finetune_codelines_pl_transform(row):
    commit_lines = row["commit_message"].splitlines()
    if len(commit_lines) > 0:
        pl = row["commit_message"].splitlines()[0]
    else:
        pl = ""
    pl += '\n' + row["code"]
    #return ' '.join(nltk.tokenize.casual_tokenize(pl))
    if pl[0] == '\n':
        pl = pl[1:]
    return pl


nl_transforms = {
    "codesearchnet": intermediate_nl_transform,
    "issue-method": finetune_nl_transform,
    "issue-codelines": finetune_nl_transform,
}

pl_transforms = {
    "codesearchnet": intermediate_pl_transform,
    "issue-method": finetune_method_pl_transform,
    "issue-codelines": finetune_codelines_pl_transform,
}
