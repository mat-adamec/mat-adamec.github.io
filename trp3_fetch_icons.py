import os
import json

icon_dir = r"E:\Games\Battle.net Games\World of Warcraft\_retail_\BlizzardInterfaceArt\Interface\ICONS"
mapping = {}

for root, dirs, files in os.walk(icon_dir):
    for file in files:
        if file.lower().endswith(".blp"):
            key = file.lower().removesuffix('.blp')                  # user might reference "pet_type_magical.blp"
            png_name = file[:-4] + ".png"       # convert to .png
            mapping[key] = png_name

# Optional: also map ".png" keys to the same target
for k in list(mapping.keys()):
    if k.endswith(".blp"):
        mapping[k[:-4] + ".png"] = mapping[k]

with open("icon_map.json", "w", encoding="utf-8") as f:
    json.dump(mapping, f, indent=2)

print("Mapping written:", len(mapping), "entries")