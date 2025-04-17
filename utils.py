import re

char_map = {'O': '0', 'I': '1', 'J': '3', 'A': '4', 'G': '6', 'S': '5'}

def correct_plate(text):
    text = text.upper().replace(" ", "")
    corrected = list(text)

    # București: B + 2 sau 3 cifre + 3 litere
    match_b = re.match(r"^B(\d{2,3})([A-Z]{3})$", text)
    if match_b:
        digits, suffix = match_b.groups()
        digits = ''.join([char_map.get(c, c) for c in digits])
        return f"B{digits}{suffix}"

    # Alte județe: 2 litere + 2 cifre + 3 litere
    match_judet = re.match(r"^([A-Z]{2})(\d{2})([A-Z]{3})$", text)
    if match_judet:
        judet, digits, suffix = match_judet.groups()
        digits = ''.join([char_map.get(c, c) for c in digits])
        return f"{judet}{digits}{suffix}"

    # Dacă nu se potrivește niciun format cunoscut, returnăm textul necorectat
    return text
