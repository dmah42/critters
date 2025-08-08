import math
import random
from simulation.models import Critter, DietType


def generate_svg(critter: Critter) -> str:
    """
    Takes a Critter and returns a string containing a
    complete procedurally generated SVG based on genetic traits
    """
    # Size affects the overall scale of the body and head.
    body_width = 35 + (critter.size * 3)
    body_height = 20 + (critter.size * 2)
    head_radius = 8 + (critter.size * 1.5)

    # Speed affects the body's sleekness and leg length.
    # A higher speed makes the body longer and thinner (more aerodynamic).
    body_width *= 1 + (critter.speed / 20)
    body_height *= 1 - (critter.speed / 20)
    leg_height = 10 + (critter.speed * 2)

    # Metabolism affects antennae length. A higher metabolism supports more complex sensory organs.
    antenna_length = 15 + (critter.metabolism * 5)

    accent_element = ""

    canvas_size = 120
    center = canvas_size / 2

    if critter.diet == DietType.HERBIVORE:
        body_color = "#6A994E"
        accent_color = "#A7C957"
        eye_color = "#344E41"

        # The number of spots is based on the critter's size.
        num_spots = int(critter.size)
        spot_radius = 2 + critter.size / 4
        spot_elements = []
        for i in range(num_spots):
            # Place spots randomly within the body's ellipse
            angle = (i / num_spots) * 2 * 3.14159
            # Use sine and cosine to distribute spots in a circular pattern
            # The random factor adds a bit of natural variation
            dist_x = (
                (body_width / 2.5) * (0.5 + random.random() * 0.5) * math.cos(angle)
            )
            dist_y = (
                (body_height / 2.5) * (0.5 + random.random() * 0.5) * math.sin(angle)
            )
            spot_cx = center + dist_x
            spot_cy = center + dist_y
            spot_elements.append(
                f'<circle cx="{spot_cx}" cy="{spot_cy}" r="{spot_radius}" fill="{accent_color}" />'
            )

        accent_element = "".join(spot_elements)

    elif critter.diet == DietType.CARNIVORE:
        body_color = "#BC4749"
        accent_color = "#A4161A"
        eye_color = "#370617"
        # Create the accent stripe element for the carnivore
        accent_element = f"""
    <rect 
        x="{center - body_width/3}" 
        y="{center + body_height/5}" 
        width="{3*body_width/4}" 
        height="{body_height/3}" 
        fill="{accent_color}" 
        rx="8" 
    />
"""
    else:  # Fallback for unknown diets
        body_color = "#CCCCCC"
        accent_color = "#999999"
        eye_color = "#333333"

    svg = f"""
<svg width="100" height="100" viewBox="0 0 {canvas_size} {canvas_size}" xmlns="http://www.w3.org/2000/svg">
    <rect width="{canvas_size}" height="{canvas_size}" fill="#FFFFFF" />

    <rect x="{center - body_width/4}" y="{center + body_height/2 - 5}" width="8" height="{leg_height}" fill="#585858" />
    <rect x="{center + body_width/4 - 8}" y="{center + body_height/2 - 5}" width="8" height="{leg_height}" fill="#585858" />

    <rect 
        x="{center - body_width/2}" y="{center - body_height/2}" 
        width="{body_width}" height="{body_height}" 
        fill="{body_color}" 
        stroke="#333" stroke-width="1" rx="15"
    />
    
    {accent_element}

    <circle cx="{center + body_width/2}" cy="{center}" r="{head_radius}" fill="{body_color}" stroke="#333" stroke-width="1" />

    <line 
        x1="{center + body_width/2}" y1="{center}" 
        x2="{center + body_width/2 + antenna_length}" y2="{center - antenna_length}" 
        stroke="#333" stroke-width="1.5" 
        transform="rotate({-10 + critter.speed}, {center + body_width/2}, {center})" 
    />
    
    <circle cx="{center + body_width/2 + head_radius/3}" cy="{center - 2}" r="3" fill="{eye_color}" />
</svg>
"""
    return svg.replace("\n", "").replace("    ", "")
