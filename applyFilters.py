import filters, random

def apply_random_filters(image):
    
    #face filters must be first
    if random.random() < 0.5:
        image = filters.text_filter(image)
    if random.random() < 0.25:
        image = filters.swirl_filter(image)

    # soft filters
    if random.random() < 0.2:
        image = filters.contrast_filter(image)
    if random.random() < 0.2:
        image = filters.saturation_filter(image)
    if random.random() < 0.2:
        image = filters.affineTransform_filter(image)
    if random.random() < 0.2:
        image = filters.vintage_filter(image)

    # medium filters (alt least one must be applied)
    medium_filter = False
    while medium_filter == False:
        if random.random() < 0.15:
            image = filters.sharpening_filter(image)
            medium_filter = True
        if random.random() < 0.15:
            image = filters.glitch_shapes_filter(image)
            medium_filter = True
        if random.random() < 0.15:
            image = filters.rotation_filter(image)
            medium_filter = True
        if random.random() < 0.15:
            if random.random() < 0.5:
                filters.green_schimmer_filter(image)
            else:
                filters.pink_schimmer_filter(image)
            medium_filter = True
        if random.random() < 0.1:
            image = filters.radial_filter(image)
            medium_filter = True
        if random.random() < 0.1:
            image = filters.color_filter(image)
            medium_filter = True
        #if random.random() < 0.05:
        #    image = filters.folding_filter(image)
        #    medium_filter = True
        if random.random() < 0.05:
            image = filters.wave_filter(image)
            medium_filter = True
    
    # heavy filters
    if random.random() < 0.05:
        image = filters.random_color_shift_filter(image)
    if random.random() < 0.05:
        image = filters.broken_rainbow_filter(image)
    #if random.random() < 0.05:
    #    image = filters.pattern_filter(image)
    if random.random() < 0.05:
        image = filters.cursed_filter(image)
    if random.random() < 0.02:
        image = filters.threshold_filter(image)

    return image
