import os
import random
import time
import json
import shutil

import cv2
import numpy as np

import image_processing.afk.detect_image_attributes as detect
import image_processing.build_db as BD


CUR_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    import image_processing.globals as GV
    SOURCE_DIR = os.path.join(GV.DATABASE_DIR, "hero_validation")

except ImportError:
    DB_DIR = os.path.join(CUR_DIR, os.pardir, os.pardir,
                          "image_processing", "database", "hero_validation")
    SOURCE_DIR = os.path.join(GV.DATABASE_DIR, "hero_validation")

HERO_SELECTION_RATIO = 0.05


def generate_data(image_name: str, image: np.array,
                  debug_raw=True):

    print(f"Starting processing {image_name}")

    start_time = time.time()
    output_dict = detect.detect_features(
        image, debug_raw=debug_raw)
    end_time = time.time()
    print(f"Image: {image_name} Elapsed: {end_time - start_time}")
    return output_dict


if __name__ == "__main__":
    files = os.listdir(SOURCE_DIR)

    sizes = []

    for _file in files:
        _file_name = os.path.join(SOURCE_DIR, _file)
        _image = cv2.imread("{}".format(_file_name))
        print(_image.shape, _file_name)
        sizes.append((_image, _file_name, _image.shape))

    sizes.sort(key=lambda x: x[2][0])

    lower = sizes[0:10]
    upper = sizes[-10:-1]
    base_heroes = sizes[10:-10]
    selection_quantity = round(len(base_heroes)*HERO_SELECTION_RATIO)
    selected_base_heroes = random.sample(base_heroes, selection_quantity)

    master_list = lower + upper + selected_base_heroes
    json_dict = {}

    for _index, _image_tuple in enumerate(master_list):
        _image = _image_tuple[0]
        _file_name = _image_tuple[1]
        new_image_name = os.path.join(
            CUR_DIR, "images", "image{}.png".format(_index))
        json_data = generate_data(json_dict, new_image_name, _image)
        print(new_image_name)
        shutil.copy(_file_name, new_image_name)
        # json_data[_file_name]["path"] = new_image_name
        with open(os.path.join(CUR_DIR,
                               "temp_validation_data.json"), "w") as f:
            json.dump(json_dict, f)

    # print("min", sizes[5:10])
    # print("max", sizes[-5:-1])
