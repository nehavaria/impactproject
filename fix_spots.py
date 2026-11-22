with open("templates/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the line with {% endif %} that comes after photo-card closing div
# Look for the pattern: </div> then blank lines then {% endif %} then blank lines then <!-- FARMING
insert_at = None
for i, line in enumerate(lines):
    if "<!-- FARMING INTELLIGENCE -->" in line:
        # Go back to find the {% endif %} before this
        for j in range(i-1, max(i-6, 0), -1):
            if "{% endif %}" in lines[j]:
                insert_at = j  # insert BEFORE this endif
                break
        break

if insert_at is None:
    print("Could not find insert point")
else:
    spots_html = """
    {% if photography.spots %}
    <div class="section-title">&#128205; Best Spots to Shoot in {{ weather.city }}</div>
    <div class="spots-grid">
        {% for spot in photography.spots %}
        <div class="spot-card">
            <div class="spot-name">{{ spot.name }}</div>
            <div class="spot-time">&#9200; Best Time: <strong>{{ spot.best_time }}</strong></div>
            <div class="spot-why">&#10024; {{ spot.why }}</div>
            <div class="spot-how">&#128652; How to reach: {{ spot.how }}</div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="spot-no-data">&#128205; Explore local parks, waterfronts and historic areas in {{ weather.city }} during golden hour for the best shots!</div>
    {% endif %}
"""
    lines.insert(insert_at, spots_html)
    with open("templates/index.html", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Inserted at line {insert_at}")
