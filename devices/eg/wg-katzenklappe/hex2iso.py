
def hex_to_iso11784(hex_str):
    # Die ersten 16 Zeichen extrahieren (64-Bit Nutzdatenblock)
    core_hex = hex_str[:16]
    val = int(core_hex, 16)

    # In 64-Bit Binärstring umwandeln und spiegeln (LSB-first Korrektur)
    bin_msb = f"{val:064b}"
    bin_lsb = bin_msb[::-1]

    # Bits nach ISO 11784 Standard extrahieren
    animal_flag = int(bin_lsb[0], 2)
    country_code = int(bin_lsb[1:11], 2)
    national_id = int(bin_lsb[11:49], 2)

    # Formatieren zu 3-stelligem Ländercode und 12-stelliger ID
    return f"country: {country_code:03d}   national_id: {national_id:012d}"

# Test mit Ihrem String
raw_rfid = "2E01A18A405830110000000000"
print("ISO 11784 ID:", hex_to_iso11784(raw_rfid))
raw_rfid = "AD01A18A405830110000000000"
print("ISO 11784 ID:", hex_to_iso11784(raw_rfid))
