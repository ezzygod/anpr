import re

# Mapare caractere asemănătoare
char_map = {
    'O': '0', 'I': '1', 'J': '3', 'A': '4', 'G': '6', 'S': '5',
    '0': 'O', '1': 'I', '3': 'J', '4': 'A', '6': 'G', '5': 'S'
}

# Lista județelor valide din România (prefixe)
judete = {
    'AB', 'AR', 'AG', 'BC', 'BH', 'BN', 'BR', 'BT', 'BV', 'BZ',
    'CS', 'CL', 'CJ', 'CT', 'CV', 'DB', 'DJ', 'GL', 'GR', 'GJ',
    'HR', 'HD', 'IL', 'IS', 'IF', 'MM', 'MH', 'MS', 'NT', 'OT',
    'PH', 'SM', 'SJ', 'SB', 'SV', 'TR', 'TM', 'TL', 'VS', 'VL',
    'VN', 'BR', 'B'  # B e București
}

def generate_variants(text):
    text = text.upper().replace(" ", "")
    variants = [[]]

    for c in text:
        new_variants = []
        mapped = char_map.get(c, c)
        for v in variants:
            new_variants.append(v + [c])  # original
            if mapped != c:
                new_variants.append(v + [mapped])  # mapat
        variants = new_variants

    return ["".join(v) for v in variants]

def correct_plate(text):
    candidates = generate_variants(text)
    seen_plates = set()

    for candidate in candidates:
        if candidate in seen_plates:
            continue

        # Validare București: B + 2-3 cifre + 3 litere
        if re.fullmatch(r"B\d{2,3}[A-Z]{3}", candidate):
            seen_plates.add(candidate)
            return candidate

        # Validare alte județe: 2 litere + 2 cifre + 3 litere
        if re.fullmatch(r"[A-Z]{2}\d{2}[A-Z]{3}", candidate):
            judet = candidate[:2]
            if judet in judete:
                seen_plates.add(candidate)
                return candidate

        # Număr roșu: 2 litere + 6 cifre
        if re.fullmatch(r"[A-Z]{2}\d{6}", candidate):
            judet = candidate[:2]
            if judet in judete:
                seen_plates.add(candidate)
                return candidate

        # București roșu: B + 6 cifre
        if re.fullmatch(r"B\d{6}", candidate):
            seen_plates.add(candidate)
            return candidate

    return None

def process_plate_detection(plates_detected):
    valid_plates = [plate for plate in plates_detected if plate and plate != "null"]
    unique_plates = []
    seen_plates = set()

    for plate in valid_plates:
        if plate['text'] not in seen_plates:
            unique_plates.append(plate)
            seen_plates.add(plate['text'])

    return unique_plates
