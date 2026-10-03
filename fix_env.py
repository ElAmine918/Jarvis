with open("/Users/amine/Code/MyCloud/.env", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith("JARVIS_API_KEY="):
        new_lines.append("JARVIS_API_KEY=\n")
    elif line.startswith("ADMIN_PASSWORD="):
        new_lines.append("ADMIN_PASSWORD=\n")
    else:
        new_lines.append(line)

with open("/Users/amine/Code/MyCloud/.env", "w") as f:
    f.writelines(new_lines)
