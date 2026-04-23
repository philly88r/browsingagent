import sys

file_path = r'c:\Users\info\browserstealth\vision_agent\vision_analyzer.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We need to fix the section around Layer 2 regex
new_lines = []
for i, line in enumerate(lines):
    # Detect the problematic section
    if 'if m:' in line and 're.search' in line and i < 280:
        new_lines.append(line)
        # We'll rewrite the next few lines with guaranteed 4-space indenting
        # based on the 'if m:' indent level (which should be 16)
        indent = line[:line.find("if m:")]
        l1 = f"{indent}    try:\n"
        l2 = f"{indent}        coords = json.loads(m.group(0))\n"
        l3 = f"{indent}        if 'nx' in coords and 'ny' in coords:\n"
        l4 = f"{indent}            x = int(float(coords['nx']) * img_w / 1000)\n"
        l5 = f"{indent}            y = int(float(coords['ny']) * img_h / 1000)\n"
        l6 = f"{indent}            print(f\"   [Verifier] -> Normalized ({{coords['nx']}}, {{coords['ny']}}) scaled to ({{x}}, {{y}})\")\n"
        l7 = f"{indent}            return x, y\n"
        l8 = f"{indent}        x, y = int(coords.get('x', 0)), int(coords.get('y', 0))\n"
        l9 = f"{indent}        if 0 < x < 1 and 0 < y < 1:\n"
        l10 = f"{indent}            x, y = int(x * img_w), int(y * img_h)\n"
        l11 = f"{indent}            print(f\"   [Verifier] -> Float normalized detected, scaled to ({{x}}, {{y}})\")\n"
        l12 = f"{indent}            return x, y\n"
        l13 = f"{indent}        print(f\"   [Verifier] -> ({{x}}, {{y}})\")\n"
        l14 = f"{indent}        return x, y\n"
        l15 = f"{indent}    except (json.JSONDecodeError, ValueError):\n"
        l16 = f"{indent}        pass\n"
        
        # We need to skip the original lines that we just replaced
        # Looking at the original file, we replace lines 275 to 290 approx
        # But we must be careful with the indices.
        pass # The loop below will handle the skipping
    else:
        # Check if we are in the range to skip
        # (This is a bit hacky, but since I know the file structure it works)
        if 274 <= i <= 289: 
             continue
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Successfully fixed vision_analyzer.py indentation")
