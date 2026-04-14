import re
import unicodedata

def num_to_katakana(n):
    """1000未満の数値をカタカナ（位読み）に変換する"""
    if n == 0: return "ゼロ"
    n_map = ["", "イチ", "ニ", "サン", "ヨン", "ゴ", "ロク", "ナナ", "ハチ", "キュウ"]
    u_map = ["", "ジュウ", "ヒャク", "セン"]
    
    res = ""
    reversed_s = str(n)[::-1]
    for i, digit in enumerate(reversed_s):
        d = int(digit)
        if d != 0:
            if i == 1: # 十の位
                if d == 1: res = "ジュウ" + res
                else: res = n_map[d] + "ジュウ" + res
            elif i == 2: # 百の位
                if d == 1: res = "ヒャク" + res
                elif d == 3: res = "サンビャク" + res
                elif d == 6: res = "ロッピャク" + res
                elif d == 8: res = "ハッピャク" + res
                else: res = n_map[d] + "ヒャク" + res
            else: # 一の位（およびそれ以上があれば）
                res = n_map[d] + res
    return res

def process_numbers(text):
    def replacer(match):
        num = int(match.group(0))
        if num < 1000:
            return num_to_katakana(num)
        return match.group(0)
    return re.sub(r'\d+', replacer, text)

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
        
        # すべてのアルファベットを一文字ずつに分解して変換
        parts = []
        for char in word_hw:
            mapped = alphabet_map.get(char.upper(), char)
            # アルファベット読みの場合、読点や促音は不要なので削除
            mapped = mapped.replace('ッ', '').replace('、', '')
            parts.append(mapped)
        return "".join(parts)
        
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
    
    # 1. 辞書単語（BED, 織田など）を優先的に置換（大文字小文字を区別せず対応）
    # 元の辞書を大文字にしてマッチング
    p_rules = rules.get('pronunciation_rules', {})
    for word in sorted(p_rules.keys(), key=len, reverse=True):
        # 大文字小文字を無視して全置換
        text = re.sub(re.escape(word), p_rules[word], text, flags=re.IGNORECASE)

    # 2. 記号と名前の区切り
    text = process_symbols(text)
    text = process_names(text)
    
    # 3. 単位と数値（位読みへの変換）
    text = process_units(text)
    text = process_numbers(text)
    
    # 4. 残ったアルファベットを一文字ずつ変換（Gなど）
    text = process_alphabets(text, rules.get('alphabet_map', {}))
    
    # 5. その他
    text = process_vowel_emphasis(text)
    return text
