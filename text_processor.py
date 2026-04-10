import re
import unicodedata

def process_names(text):
    return text.replace('　', '、').replace(' ', '、')

def process_symbols(text):
    text = text.replace('(', '……').replace('（', '……')
    text = text.replace(')', '……').replace('）', '……')
    
    # ★変更点: 前の文字が何であっても、すべてのハイフン・ダッシュ・アンダーバーを「の」に変換
    text = re.sub(r'[-－‐_＿]', 'の', text)
    
    text = text.replace('：', '、').replace(':', '、')
    return text

def process_units(text):
    return re.sub(r'(\d+)[FfＦｆ]', r'\1かい', text)

def process_alphabets(text, alphabet_map):
    def replacer(match):
        word = match.group(0)
        word_hw = unicodedata.normalize('NFKC', word)
        
        if len(word_hw) == 1:
            mapped = alphabet_map.get(word_hw.upper(), word_hw)
            return mapped.replace('ッ', '').replace('、', '')
            
        if word_hw.isupper():
            parts = []
            for char in word_hw:
                mapped = alphabet_map.get(char, char)
                mapped = mapped.replace('ッ', '').replace('、', '')
                parts.append(mapped)
            return "".join(parts)
            
        return word_hw
        
    return re.sub(r'[a-zA-Zａ-ｚＡ-Ｚ]+', replacer, text)

def process_vowel_emphasis(text):
    """
     Kokoroエンジンの場合、間を開けた直後のア行の発音は自然に処理されるため、
    「！」を入れると逆に不自然なスパイク音を誘発します。そのため処理を無効化しています。
    """
    return text

def process_dictionary(text, rules):
    for word, reading in rules.get('pronunciation_rules', {}).items():
        text = text.replace(word, reading)
    return text

def apply_rules(text, rules):
    if not isinstance(text, str): return ""
    text = process_symbols(text)
    text = process_names(text)
    text = process_units(text)
    text = process_alphabets(text, rules.get('alphabet_map', {}))
    text = process_vowel_emphasis(text)
    text = process_dictionary(text, rules)
    return text
