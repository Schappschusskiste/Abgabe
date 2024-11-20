import skimage as ski
import numpy as np
import random

from skimage.transform import PiecewiseAffineTransform, warp
from faceFilters import swirl_filter, text_filter

# Alle Filter die man benutzen kann:
#image = filters.swirl_filter(image)
#image = filters.text_filter(image)
#image = filters.wave_filter(image)
#image = filters.folding_filter(image) # raus genommen, weil zu langsam
#image = filters.radial_filter(image)
#image = filters.cursed_filter(image)
#image = filters.color_filter(image)
#image = filters.glitch_shapes_filter(image)
#image = filters.broken_rainbow_filter(image)
#image = filters.pattern_filter(image) # raus genommen, weil zu langsam
#image = filters.random_color_shift_filter(image)
#image = filters.contrast_filter(image)
#image = filters.saturation_filter(image)
#image = filters.sharpening_filter(image)
#image = filters.threshold_filter(image)
#image = filters.rotation_filter(image)
#image = filters.affineTransform_filter(image)
#image = filters.vintage_filter(image)
#image = filters.green_schimmer_filter(image)
#image = filters.pink_schimmer_filter(image)


# startregion definitions
def convert_image(image):
    image_uint8 = (image * 255).astype(np.uint8)
    return image_uint8

def radial_distortion(xy):
    xy_c = xy.max(axis=0) / 2
    xy = (xy - xy_c) / xy_c
    radius = np.linalg.norm(xy, axis=1)
    k1 = random.uniform(0.7, 1.0)
    k2 = random.uniform(0.2, 0.4)
    distortion_model = (1 + k1 * radius + k2 * radius**2) * k2
    xy *= distortion_model.reshape(-1, 1)
    xy = xy * xy_c + xy_c
    return xy

def biased_random(min, max):
    # This will make lower numbers more likely
    x = np.random.power(0.5)
    # Scale the number to the range [min, max]
    return min + ((max-1.0) * x)
# endregion

# startregion filters
def wave_filter(image):
    rows, cols = image.shape[0], image.shape[1]
    src_cols = np.linspace(0, cols, random.randint(3,20))
    src_rows = np.linspace(0, rows, 10)
    src_rows, src_cols = np.meshgrid(src_rows, src_cols)
    src = np.dstack([src_cols.flat, src_rows.flat])[0]
    # add sinusoidal oscillation to row coordinates
    dst_rows = src[:, 1] - np.sin(np.linspace(0, 3 * np.pi, src.shape[0])) * random.randint(100,200)
    dst_cols = src[:, 0]
    dst_rows *= 1.5
    dst_rows -= 1.5 * random.randint(10,100)
    dst = np.vstack([dst_cols, dst_rows]).T
    tform = PiecewiseAffineTransform()
    tform.estimate(src, dst)
    out_rows = image.shape[0] - 1.5 * 50
    out_cols = cols
    out = warp(image, tform, output_shape=(out_rows, out_cols))
    return convert_image(out)

def folding_filter(image):
    rows, cols = image.shape[0], image.shape[1]
    
    # Randomize the source columns and rows
    num_cols = random.randint(10, 40)
    num_rows = random.randint(10, 20)
    src_cols = np.random.choice(np.arange(cols), num_cols, replace=False)
    src_rows = np.random.choice(np.arange(rows), num_rows, replace=False)
    src_rows, src_cols = np.meshgrid(src_rows, src_cols)
    src = np.dstack([src_cols.flat, src_rows.flat])[0]
    
    # Add sinusoidal oscillation to row coordinates
    dst_rows = src[:, 1] - np.sin(np.linspace(0, 3 * np.pi, src.shape[0])) * 50
    dst_cols = src[:, 0]
    dst_rows *= 1.5
    dst_rows -= 1.5 * 100
    dst = np.vstack([dst_cols, dst_rows]).T

    tform = PiecewiseAffineTransform()
    tform.estimate(src, dst)

    out_rows = int(rows - 1.5 * 50)  # Ensure out_rows is an integer
    out_cols = cols
    out = warp(image, tform, output_shape=(out_rows, out_cols))
    return convert_image(out)


def radial_filter(image):
    image = warp(image, radial_distortion, cval=0.5)
    return convert_image(image)


def cursed_filter(image):
    hsv_img = ski.color.rgb2hsv(image)
    hue_img = hsv_img[:, :, random.randint(-1,1)]
    rgb_image = ski.color.gray2rgb(hue_img)
    return convert_image(rgb_image)

def color_filter(image):
    multiplier = [0,0,0]
    rand1 = random.randint(0, 2)
    rand2 = random.randint(0, 2)
    multiplier[rand1] = 1
    multiplier[rand2] = 1
    image = image * multiplier
    return convert_image(image)

def random_color_shift_filter(image):
    multiplier = [random.uniform(-1, 1),random.uniform(-1, 1),random.uniform(-1, 1)]
    image = image + multiplier
    return convert_image(image)

def glitch_shapes_filter(image):
    height, width = image.shape[:2]
    shape_image, _ = ski.draw.random_shapes(
        (height, width), min_shapes=5, max_shapes=10, min_size=20, allow_overlap=True
    )
    rotated_shapes = ski.transform.swirl(shape_image, rotation=random.uniform(-5.0, 5.0))
    return image + convert_image(rotated_shapes)

def broken_rainbow_filter(image):
    image = ski.exposure.rescale_intensity(image, out_range=(0, random.uniform(0.4, 2.5) * np.pi))
    image_wrapped = np.angle(np.exp(1j * image))
    return convert_image(image_wrapped)

def pattern_filter(image):
    labels1 = ski.segmentation.slic(image, compactness=random.randint(1,50), n_segments=random.randint(100,1000), start_label=1)
    image = ski.color.label2rgb(labels1, image, kind='avg', bg_label=0)
    return image

def contrast_filter(image):
    image = ski.exposure.adjust_gamma(image, gamma=random.uniform(0.1, 5))
    return image

def saturation_filter(image):
    saturation_factor = random.uniform(0.1, 3)
    image = ski.color.rgb2hsv(image)
    image[..., 1] = np.clip(image[..., 1] * saturation_factor, 0, 1)
    image = ski.color.hsv2rgb(image)
    return convert_image(image)

def sharpening_filter(image):
    image = ski.filters.unsharp_mask(image, biased_random(0.0, 20.0), random.uniform(-10.0, 10.0))
    return convert_image(image)

def threshold_filter(image):
    image = ski.color.rgb2gray(image)
    thresh = ski.filters.threshold_otsu(image, nbins=random.randint(2,20))
    image = image > thresh
    return convert_image(image)

def rotation_filter(image):
    image = ski.transform.swirl(image, rotation=random.uniform(-5.0, 5.0))
    return convert_image(image)

def affineTransform_filter(image):
    tform = ski.transform.AffineTransform(scale=(1, 1), rotation=random.uniform(0.1,-0.1), shear=random.uniform(-0.3,0.3))
    transformed_image = ski.transform.warp(image, tform)
    return convert_image(transformed_image)

def vintage_filter(image):
    image = ski.filters.gaussian(image, mode=random.choice(['reflect', 'constant', 'nearest', 'mirror', 'wrap']), cval=random.uniform(-0.1,1), truncate=random.uniform(0,4))
    return convert_image(image)

def green_schimmer_filter(image):
    image = ski.morphology.dilation(image, mode='constant', cval=random.uniform(0,250))
    return convert_image(image)

def pink_schimmer_filter(image):
    image = ski.morphology.erosion(image, mode='constant', cval=random.uniform(-250,250))
    return convert_image(image)
# endregion