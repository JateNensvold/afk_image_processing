import cv2
import os
import csv
import image_processing.build_db as BD
import image_processing.globals as GV
import image_processing.load_images as load
import image_processing.processing as processing
import image_processing.stamina as stamina
import collections
import numpy as np
import image_processing.scripts.getSISize as siScript
import multiprocessing
import json


def rollingAverage(avg, newSample, size):
    avg -= avg / size
    avg += newSample/size
    return avg


def get_si(image, image_name, debug_raw=False, imageDB=None):
    if imageDB is None:
        imageDB = BD.get_db(enrichedDB=True)

    baseImages = collections.defaultdict(dict)

    image_0 = cv2.imread(os.path.join(GV.siBasePath, "0", "0.png"))
    image_10 = cv2.imread(os.path.join(GV.siBasePath, "10", "10.png"))
    image_20 = cv2.imread(os.path.join(GV.siBasePath, "20", "20.png"))
    image_30 = cv2.imread(os.path.join(GV.siBasePath, "30", "30.png"))

    fi_base_images = collections.defaultdict(dict)

    fi_3_image = cv2.imread(os.path.join(GV.fi_base_path, "3", "3fi.png"))
    fi_9_image = cv2.imread(os.path.join(GV.fi_base_path, "9", "9fi.png"))

    baseImages["3"]["image"] = fi_3_image
    baseImages["3"]["crop"] = fi_3_image[0:, 0:]
    baseImages["3"]["contourNum"] = 1

    baseImages["9"]["image"] = fi_9_image
    baseImages["9"]["crop"] = fi_9_image[0:, 0:]
    baseImages["9"]["contourNum"] = 1

    baseImages["0"]["image"] = image_0
    baseImages["0"]["contourNum"] = 2
    # baseImages["0"]["height"] = 52.6
    # baseImages["0"]["width"] = 52.06666666666667

    x, y, _ = image_10.shape
    newx = int(x*0.7)
    newy = int(y*0.6)
    baseImages["10"]["image"] = image_10
    baseImages["10"]["crop"] = image_10[0:, 0:]
    baseImages["10"]["contourNum"] = 3
    baseImages["10"]["morph"] = True
    # baseImages["10"]["height"] = 63
    # baseImages["10"]["width"] = 63.52173913043478

    x, y, _ = image_20.shape

    starty = int(y*0.45)
    endx = int(x*0.5)
    baseImages["20"]["image"] = image_20
    baseImages["20"]["crop"] = image_20[0:, 0:endx]
    baseImages["20"]["contourNum"] = 2
    # baseImages["20"]["height"] = 75.1891891891892
    # baseImages["20"]["width"] = 64.27027027027027

    # newx = int(x*0.5)
    # newy = int(y*0.2)
    # baseImages["30"]["image"] = image_30
    # baseImages["30"]["crop"] = image_30[0:newy, 0:]
    # baseImages["30"]["contourNum"] = 1
    x, y, _ = image_30.shape
    newx = int(x*0.3)
    newy = int(y*0.7)
    baseImages["30"]["image"] = image_30
    baseImages["30"]["crop"] = image_30[0:newy, 0:newx]
    baseImages["30"]["contourNum"] = 1
    # baseImages["30"]["height"] = 78.23076923076923
    # baseImages["30"]["width"] = 79.94871794871794

    csvfile = open(
        "/home/nate/projects/afk-image-processing/image_processing/scripts/lvl_txt_si_scale.txt",
        "r")

    header = ["digitName", "si_name", "v_scale"]

    reader = csv.DictReader(csvfile, header)

    for row in reader:
        _digit_name = row["digitName"]
        _si_name = row["si_name"]
        _v_scale = float(row["v_scale"])
        if _digit_name not in baseImages[_si_name]:
            baseImages[_si_name][_digit_name] = {}
        baseImages[_si_name][_digit_name]["v_scale"] = _v_scale

    hero_ss = image

    # (hMin = 0 , sMin = 68, vMin = 170), (hMax = 35 , sMax = 91, vMax = 255)
    # lower_hsv = np.array([0, 68, 170])
    # upper_hsv = np.array([35, 91, 255])

    # (hMin = 23 , sMin = 0, vMin = 0), (hMax = 179 , sMax = 255, vMax = 255)
    # lower_hsv = np.array([23, 0, 0])
    # upper_hsv = np.array([179, 255, 255])

    # (hMin = 12 , sMin = 75, vMin = 212), (hMax = 23 , sMax = 109, vMax = 253)
    # lower_hsv = np.array([12, 75, 212])
    # upper_hsv = np.array([23, 109, 253])

    # (hMin = 5 , sMin = 79, vMin = 211), (hMax = 21 , sMax = 106, vMax = 250)
    lower_hsv = np.array([0, 0, 0])
    upper_hsv = np.array([179, 255, 192])

# (hMin = 0 , sMin = 0, vMin = 0), (hMax = 179 , sMax = 255, vMax = 192)

    hsv_range = [lower_hsv, upper_hsv]
    blur_args = {"hsv_range": hsv_range}
    heroesDict, rows = processing.getHeroes(
        hero_ss, blur_args=blur_args)

    circle_fail = 0

    digit_bins = {}

    for k, v in heroesDict.items():
        bins = siScript.getDigit(v["image"])
        v["digit_info"] = bins
        for digitName, tempDigitdict in bins.items():

            digitTuple = tempDigitdict["digit_info"]
            digitTop = digitTuple[0]
            digitBottom = digitTuple[1]
            digitHeight = digitBottom - digitTop
            if digitName not in digit_bins:
                digit_bins[digitName] = []
            digit_bins[digitName].append(digitHeight)
    avg_bin = {}
    total_digit_occurrences = 0
    for k, v in digit_bins.items():
        avg = np.mean(v)
        avg_bin[k] = {}
        avg_bin[k]["height"] = avg
        occurrence = len(v)
        avg_bin[k]["count"] = occurrence
        total_digit_occurrences += occurrence

    graded_avg_bin = {}
    for si_name, image_dict in baseImages.items():
        if si_name not in graded_avg_bin:
            graded_avg_bin[si_name] = {}
        frequency_height_adjust = 0
        for digit_name, scale_dict in avg_bin.items():

            v_scale = baseImages[si_name][digit_name]["v_scale"]

            digit_count = scale_dict["count"]
            digit_height = scale_dict["height"]
            digit_freqency = digit_count / total_digit_occurrences

            frequency_height_adjust += (v_scale *
                                        digit_height) * digit_freqency
        graded_avg_bin[si_name]["height"] = frequency_height_adjust

    si_dict = stamina.signature_template_mask(baseImages)
    fi_dict = stamina.furniture_template_mask(baseImages)

    if not GV.DEBUG and GV.PARALLEL:
        pool = multiprocessing.Pool()

        all_args = [({"name": _hero_name, "info": _hero_info_dict,
                      "si_dict": si_dict,
                      "graded_avg_bin": graded_avg_bin,
                      "fi_dict": fi_dict, }
                     )for _hero_name, _hero_info_dict in heroesDict.items()]

        reduced_values = pool.map(parallel_detect, all_args)
    else:
        reduced_values = []
        for _hero_name, _hero_info_dict in heroesDict.items():
            reduced_values.append(parallel_detect(
                {"name": _hero_name,
                 "info": _hero_info_dict,
                 "si_dict": si_dict,
                 "fi_dict": fi_dict,
                 "graded_avg_bin": graded_avg_bin}))

    return_dict = {}

    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 3
    color = (255, 255, 0)
    thickness = 2

    for _hero_data in reduced_values:
        # name = "{}{}".format(_hero_data["si"], _hero_data["fi"])
        name = _hero_data["pseudo_name"]
        result = _hero_data["result"]
        coords = _hero_data["coords"]
        # hero_name, baseHeroImage = imageDB.search(v["image"])
        hero_name, _ = imageDB.search(heroesDict[name]["image"])
        result = "{} {}".format(hero_name, result)
        _hero_data["result"] = result
        return_dict[name] = _hero_data
        # if "display" in _hero_data:
        #     print("Failed to find fi score")
        #     load.display_image(heroesDict[name]["image"], display=True)
        fontScale = 0.5 * (rows[0][0][0][-1]/100)

        text_size = cv2.getTextSize(result, font, fontScale, thickness)
        height = text_size[0][1]
        coords = (coords[0], coords[1] + height)
        cv2.putText(
            hero_ss, result, coords, font, fontScale, color, thickness,
            cv2.LINE_AA)
    # test_names = set(_hero_name for _hero_name,
    #                  _hero_info_dict in heroesDict.items())
    # return_names = set(return_dict.keys())
    json_dict = {}
    json_dict[image_name] = {}
    json_dict[image_name]["rows"] = len(rows)
    json_dict[image_name]["columns"] = max([len(_row) for _row in rows])

    json_dict[image_name]["heroes"] = []
    # output_set = set(sorted(output.keys()))

    for _row in rows:
        temp_list = []
        for _index in range(len(_row)):
            hero_data = []
            temp = return_dict[_row[_index][1]]["result"]
            hero_data.append(temp)
            if debug_raw:
                _raw_score = return_dict[_row[_index][1]]["score"]
                hero_data.append(_raw_score)
            temp_list.append(hero_data)
        json_dict[image_name]["heroes"].append(temp_list)
    return json_dict


def parallel_detect(info_dict):
    k = info_dict["name"]
    v = info_dict["info"]
    si_dict = info_dict["si_dict"]
    fi_dict = info_dict["fi_dict"]

    graded_avg_bin = info_dict["graded_avg_bin"]
    # for k, v in heroes_dict.items():
    # heroes_dict[k]["label"] = name
    return_dict = {}
    si_scores = stamina.signatureItemFeatures(
        v["image"], si_dict, graded_avg_bin)
    fi_scores = stamina.furnitureItemFeatures(
        v["image"], fi_dict, graded_avg_bin)
    x = v["object"][0][0]
    y = v["object"][0][1]
    if fi_scores["9"] == 0 or fi_scores["3"] == 0:
        return_dict["display"] = True
    if fi_scores["9"] > 0.7:
        best_fi = "9"
    elif fi_scores["3"] > 0.5:
        best_fi = "3"
    else:
        best_fi = "0"

    if si_scores == -1:
        # circle_fail += 1
        best_si = "none"
    else:
        if si_scores["30"] > 0.6:
            best_si = "30"
        elif si_scores["20"] > 0.7:
            best_si = "20"
        elif si_scores["10"] > 0.50:
            best_si = "10"
        else:
            # si_label_list = ["0", "10"]
            # # key=lambda x: heroes[x[0][1]]["dimensions"]["y"][0]
            # best_si = max(si_label_list, key=lambda x: si_scores[x])
            # best_si_score = si_scores[best_si]
            # if best_si_score < 0.4:
            #     # best_si = "n/a"
            best_si = "00"

    coords = (x, y)
    # name = "{},{}".format(name, best_si)
    # name = "{} s:{:.3}".format(best_fi, fi_score)
    name = "{}{}".format(best_si, best_fi)
    # print("pid: {} name:{} stat:{}".format(
    #     multiprocessing.current_process().pid, k, name))
    return_dict["si"] = best_si
    return_dict["fi"] = best_fi
    return_dict["score"] = si_scores
    return_dict["result"] = name
    return_dict["pseudo_name"] = k
    return_dict["coords"] = coords
    # return_dict["name"] = hero
    return return_dict


if __name__ == "__main__":
    # pool = multiprocessing.Pool()
    json_dict = get_si(GV.image_ss, GV.image_ss_name, debug_raw=True,)
    load.display_image(GV.image_ss, display=True)

    print(json_dict)
    # with open("temp.json", "w") as f:
    #     json.dump(json_dict, f)
