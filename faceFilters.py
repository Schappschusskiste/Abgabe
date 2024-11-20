import skimage as ski
import numpy as np
import random
import matplotlib
import matplotlib.pyplot as plt

from PIL import Image

matplotlib.use("agg")

def convert_image(image):
    image_uint8 = (image * 255).astype(np.uint8)
    return image_uint8

def face_detection(image):
    # startregion Face detection
    trained_file = ski.data.lbp_frontal_face_cascade_filename()
    detector = ski.feature.Cascade(trained_file)
    detected = detector.detect_multi_scale(
        img=image, scale_factor=1.2, step_ratio=1, min_size=(100, 100), max_size=(1000, 1000)
    )
    center_x = 0
    center_y = 0

    # get x, y
    for face in detected:
        # Calculate the center of the face
        center_y = face['r'] + face['width'] // 2
        center_x = face['c'] + face['height'] // 2
        return center_x, center_y   # only return the first face
    else:
        #if there are no faces found
        height, width = image.shape[:2]
        center_x = width // 2
        center_y = height // 2
        return center_x, center_y

def swirl_filter(image):
    x, y = face_detection(image)
    image = ski.transform.swirl(image, strength=random.uniform(-5,5), radius=random.uniform(1400,1500), center=(x, y))
    return convert_image(image)

def random_schnappi_text():
    with open('schnappi_text.txt', 'r', encoding='utf-8') as file:
        lines = file.readlines()
    random_line = random.choice(lines)
    return random_line.strip()

def text_filter(image):
    fig = plt.figure()
    fig.figimage(image, resize=True)
    x, y = face_detection(image)
    height, width = image.shape[:2]
    fig.text(x=(x/width), y=(y/height)-0.1, s=random_schnappi_text(), fontsize=random.uniform(20,32), ha="center", va="center", color=(random.uniform(0,1),random.uniform(0,1),random.uniform(0,1)), rotation=random.uniform(-45,45))
    fig.canvas.draw()
    annotated_img = np.asarray(fig.canvas.renderer.buffer_rgba())
    plt.close(fig)
    pil_image = Image.fromarray(annotated_img)
    rgb_image = pil_image.convert('RGB')
    return np.array(rgb_image)