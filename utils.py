# utils.py - Funcții pentru mapare caractere și salvare CSV
import csv
import re

# Dicționar pentru corectarea caracterelor
char_map = {'O': '0', 'I': '1', 'J': '3', 'A': '4', 'G': '6', 'S': '5'}

# Aplică maparea doar la pozițiile numerice corecte
def correct_plate(text):
    corrected = list(text)
    
    # Identificăm structura standard: 2 litere + 2 cifre + 3 litere
    pattern = re.match(r"([A-Z]{2})(\d{2})([A-Z]{3})", text)
    if pattern:
        prefix, num, suffix = pattern.groups()
        num = "".join([char_map[c] if c in char_map else c for c in num])  # Corectăm doar cifrele
        return f"{prefix}{num}{suffix}"
    
    return text  # Returnăm originalul dacă nu respectă formatul

def save_to_csv(data, filename="plates.csv"):
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        for row in data:
            writer.writerow(row)
