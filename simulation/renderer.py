from simulation.models import Critter, DietType


def generate_svg(critter: Critter) -> str:
    """
    Takes a Critter and returns a string containing a
    complete procedurally generated SVG based on genetic traits
    """
    # Translate genes into visual properties
    body_width = 40 + (critter.size * 4)
    base_body_height = 25 + (critter.size * 3)

    # Speed affects leg length
    leg_height = 10 + (critter.speed * 2)

    # Metabolism acts as a MULTIPLIER on the base height.
    # A low metabolism (e.g., 0.8) makes the critter taller/rounder.
    # A high metabolism (e.g., 1.2) makes it shorter/flatter.
    metabolism_modifier = 1 / critter.metabolism
    final_body_height = base_body_height * metabolism_modifier

    # Diet determines colour palette
    if critter.diet == DietType.HERBIVORE:
        body_color = "#6A994E"
        eye_color = "#344E41"
    elif critter.diet == DietType.CARNIVORE:
        body_color = "#BC4749"
        eye_color = "#A4161A"
    else:
        body_color = "#CCCCCC"
        eye_color = "#333333"

    # We use an f-string to inject our calculated properties into the SVG XML.
    # The viewBox defines the "canvas" size for our drawing.
    svg = f"""
<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
<!-- Simple background -->
<rect width="100" height="100" fill="#f0f0f0" />

<!-- Legs (drawn first, so they are behind the body) -->
<rect x="{50 - body_width/3}" y="{50 + final_body_height/2 - 5}" width="8" height="{leg_height}" fill="#585858" />
<rect x="{50 + body_width/3 - 8}" y="{50 + final_body_height/2 - 5}" width="8" height="{leg_height}" fill="#585858" />

<!-- Body -->
<ellipse 
    cx="50" 
    cy="50" 
    rx="{body_width / 2}" 
    ry="{final_body_height / 2}" 
    fill="{body_color}" 
    stroke="#333" 
    stroke-width="1"
/>

<!-- Eye -->
<circle cx="{50 + body_width/4}" cy="45" r="4" fill="{eye_color}" />
</svg>
"""
    return svg
