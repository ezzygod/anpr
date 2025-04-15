import re

# Dicționar pentru corectarea caracterelor care pot fi OCR-uite greșit
char_map = {'O': '0', 'I': '1', 'J': '3', 'A': '4', 'G': '6', 'S': '5'}

# Coduri județe valide
judete = {
    'AB', 'AR', 'AG', 'BC', 'BH', 'BN', 'BR', 'BT', 'BV', 'BZ',
    'CS', 'CL', 'CJ', 'CT', 'CV', 'DB', 'DJ', 'GL', 'GR', 'GJ',
    'HR', 'HD', 'IL', 'IS', 'IF', 'MM', 'MH', 'MS', 'NT', 'OT',
    'PH', 'SM', 'SJ', 'SB', 'SV', 'TR', 'TM', 'TL', 'VS', 'VL', 'VN'
}

def correct_plate(text):
    original = text.upper().replace(" ", "")
    corrected = ''.join([char_map.get(c, c) for c in original])

    # 1. București standard: B + 2-3 cifre + 3 litere
    if re.fullmatch(r"B\d{2,3}[A-Z]{3}", corrected):
        return corrected

    # 2. București roșu: B + 6 cifre
    if re.fullmatch(r"B\d{6}", corrected):
        return corrected

    # 3. Alte județe standard: 2 litere + 2 cifre + 3 litere
    if re.fullmatch(r"[A-Z]{2}\d{2}[A-Z]{3}", corrected):
        if corrected[:2] in judete:
            return corrected

    # 4. Alte județe roșii: 2 litere + 6 cifre
    if re.fullmatch(r"[A-Z]{2}\d{6}", corrected):
        if corrected[:2] in judete:
            return corrected

    # Nimic valid? Returnăm None
    return None
