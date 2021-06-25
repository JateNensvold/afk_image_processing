import os
import json
import cv2

import numpy as np
import matplotlib.pyplot as plt
import image_processing.load_images as load
import image_processing.processing as processing
import image_processing.globals as GV
import imutils
# Need this import to use imutils.contours.sort_contours,
#   without it Module raises AttributeError
from imutils import contours  # noqa


def sort_row(row: list, heroes: dict):
    return sorted(row, key=lambda x: heroes[x[1]]["dimensions"]["x"][0])


class row():
    """
    """

    def __str__(self):
        return "".join([str(_row) for _row in self._list])

    def __iter__(self):
        return self

    def __next__(self) -> tuple:
        self._idx += 1
        try:
            return self._list[self._idx - 1]
        except IndexError:
            self._idx = 0
            raise StopIteration

    def __len__(self):
        return len(self._list)

    def __init__(self):
        self._items = {}
        self._list = []
        self._idx = 0

        self.head = None

    def get_head(self):
        return self.head

    def get(self, name: str):
        """
        Get an item by its associated name
        Args:
            name: name of image that is associated with location in row

        Returns tuple(x_coord, y_coord, image_name), index
        """
        _index = self._items[name]
        return self._list[_index], _index

    def __getitem__(self, index: int):
        """
        Get an item by its index
        Args:
            index: position of item in row

        Returns tuple(x_coord, y_coord, image_name)
        """
        return self._list[index]

    def append(self, dimensions, name, detect_collision=True):
        """
        Adds a new entry to Row
        Args:
            dimensions: x,y,w,h of object
            name: identifier for row item, can be used for lookup later
            detect_collision: check for object overlap/collisions when
                appending to row
        Return:
            None
        """
        if len(self._list) == 0:
            self.head = dimensions[1]
        self._items[name] = len(self._items)
        if detect_collision:
            if self.check_collision((dimensions, name)) == -1:
                self._list.append((dimensions, name))
        else:
            self._list.append((dimensions, name))

    def check_collision(self, collision_object: tuple,
                        size_allowance_boundary: int = 0.25) -> int:
        """
        Check if collision_object's dimensions overlap with any of the objects
            in the row object, and merge collision_object with overlaping
            object if collisions is detected

        Args:
            collision_object: new row object to check against existing row
                objects
            size_allowance_boundary: percent size that collision image must be
                within the average of all other images in row

        Return: index of updated row object when collisions occurs, -1
            otherwise
        """

        for _index, _row_object in enumerate(self._list):
            ax1 = _row_object[0][0]
            ax2 = _row_object[0][0] + _row_object[0][2]
            ay1 = _row_object[0][1]
            ay2 = _row_object[0][1] + _row_object[0][3]

            bx1 = collision_object[0][0]
            bx2 = collision_object[0][0] + collision_object[0][2]
            by1 = collision_object[0][1]
            by2 = collision_object[0][1] + collision_object[0][3]

            if ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1:
                new_x = min(ax1, bx1)
                new_y = min(ay1, by1)
                new_w = (max(ax2, bx2) - new_x)
                new_h = (max(ay2, by2) - new_y)
                avg_w = np.mean([_object[0][2] for _object in self._list])
                avg_h = np.mean([_object[0][3] for _object in self._list])
                if (abs(avg_w - new_w) < avg_w * size_allowance_boundary) and \
                        (abs(avg_h - new_h) < avg_h * size_allowance_boundary):

                    dimensions = (new_x, new_y, new_w, new_h)
                    self._list[_index] = (dimensions, _row_object[1])
                    return _index
                else:
                    print("row: {} Collision failed beteween "
                          "({}) and ({})".format(self, _row_object,
                                                 collision_object))
        return -1

    def sort(self):
        '''
        Sort the internal data structure by x coordinate of each item

        Args:
            None
        Return:
            None
        '''
        self._list.sort(key=lambda x: x[0][0])
        for _index, _entry in enumerate(self._list):
            self._items[_entry[1]] = _index


class matrix():
    """
    """

    def __str__(self):
        return "\n".join([str(_row) for _row in self._row_list])

    def __iter__(self):
        return self

    def __next__(self) -> row:
        self._idx += 1
        try:
            return self._row_list[self._idx - 1]
        except IndexError:
            self._idx = 0
            raise StopIteration

    def __len__(self):
        return len(self._row_list)

    def __init__(self, spacing=10):
        self.spacing = spacing
        self._heads = {}
        self._row_list = []
        self._idx = 0

    def auto_append(self, dimensions, name, detect_collision=True):
        """
        Add a new entry into the matrix, either creating a new row or adding to
            an existing row depending on `spacing` settings and distance.
        Args:
            dimensions: x,y,w,h of object
            name: identifier for object
            detect_collision: check for object overlap/collisions when
                appending to row
        Return:
            None
        """
        # self._lists.append(row)
        y = dimensions[1]
        _row_index = None
        for _index, _head in self._heads.items():
            # If there are no close rows set flag to create new row
            if abs(_head() - y) < self.spacing:
                _row_index = _index
                break
        if _row_index is not None:
            self._row_list[_row_index].append(
                dimensions, name, detect_collision=detect_collision)
        else:
            _temp_row = row()
            _temp_row.append(dimensions, name,
                             detect_collision=detect_collision)
            self._heads[len(self._row_list)] = _temp_row.get_head
            self._row_list.append(_temp_row)

    def sort(self):
        for _row in self._row_list:
            _row.sort()
        self._row_list.sort(key=lambda _row: _row.head)

    def prune(self, threshold):
        """
        Remove all rows that have a length less than the `threshold`

        Args:
            threshold: limit that determines if a row should be pruned when
                its length is less than this
        Return:
            None
        """
        _prune_list = []
        for _index, _row_object in enumerate(self._row_list):
            if len(_row_object) < threshold:
                _prune_list.append(_index)
        if len(_prune_list) > 0:
            print("Deleting ({}) row objects({}) from matrix. Ensure that "
                  "getHeroes was successful".format(
                      len(_prune_list), _prune_list))
            for _index in _prune_list:
                print("Deleted row object ({}) of len ({})".format(
                    self._row_list[_index], len(self._row_list[_index])))
                self._row_list.pop(_index)
                del self._heads[_index]


def generate_rows(heroes: dict, spacing: int = 10):
    """
    Args:
        heroes: dictionary of image data to use as a lookup table
        spacing: number of pixels an image has to be away from an existing row
            to signal for the creation of a new row

    Return:
        list of lists of tuples(label, name, image)
    """
    rows = []
    heads = {}
    for k, v in heroes.items():
        y = v["dimensions"]["y"][0]
        x = v["dimensions"]["x"][0]

        closeRow = False
        index = None
        for head, headIndex in heads.items():
            # If there are no close rows set flag to create new row
            if abs(head - y) < spacing:
                closeRow = True
                index = headIndex
                break

        if not closeRow:
            rows.append(row())
            heads[y] = len(rows) - 1
            index = heads[y]
        rows[index].append(x, y, k)
    rows = sorted(rows, key=lambda x: heroes[x[0][1]]["dimensions"]["y"][0])
    for i in range(len(rows)):
        newRow = sort_row(rows[i], heroes)
        rows[i] = newRow

    return rows


# def merge_rows(*args):
#     master_row = []
#     for head, headIndex in heads.items():
#         # If there are no close rows set flag to create new row
#         if abs(head - y) < spacing:
#             closeRow = True
#             index = headIndex
#             break


def get_stamina_area(rows: list, heroes: dict, sourceImage: np.array):
    numRows = len(rows)
    staminaCount = {}
    # iterate across length of row
    averageHeight = 0
    samples = 0
    for j in range(numRows):
        for i in range(len(rows[j])):
            # iterate over column
            # Last row
            unitName = rows[j][i][1]
            y = heroes[unitName]["dimensions"]["y"]
            x = heroes[unitName]["dimensions"]["x"]
            gapStartX = x[0]
            gapStartY = y[1]
            gapWidth = x[1] - x[0]
            if (j + 1) == numRows:
                gapBottom = gapStartY + int(averageHeight)
            else:
                gapBottom = heroes[rows[j+1][i][1]]["dimensions"]["y"][0]

                samples += 1
                a = 1/samples
                b = 1 - a
                averageHeight = (a * (gapBottom - gapStartY)
                                 ) + (b * averageHeight)
            staminaArea = sourceImage[gapStartY:gapBottom,
                                      gapStartX:gapStartX + gapWidth]
            staminaCount[unitName] = staminaArea

    return staminaCount


def get_text(staminaAreas: dict, train: bool = False):

    # build template dictionary
    digits = {}
    numbersFolder = GV.staminaTemplatesPath
    # numbersFolder = os.path.join(os.path.dirname(
    #     os.path.abspath(__file__)), "numbers")

    referenceFolders = os.listdir(numbersFolder)
    for folder in referenceFolders:
        if folder not in digits:
            digits[folder] = {}
        digitFolder = os.path.join(numbersFolder, folder)
        for i in os.listdir(digitFolder):
            name, ext = os.path.splitext(i)
            digits[folder][name] = cv2.imread(os.path.join(digitFolder, i))
    output = {}
    for name, stamina_image in staminaAreas.items():
        original = stamina_image.copy()

        lower = np.array([0, 0, 176])
        upper = np.array([174, 34, 255])
        hsv = cv2.cvtColor(stamina_image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        result = cv2.bitwise_and(original, original, mask=mask)
        print("original", original.shape)
        print("mask", mask.shape)
        result[mask == 0] = (255, 255, 255)

        result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        result = cv2.threshold(
            result, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY)[1]

        digitCnts = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        digitCnts = imutils.grab_contours(digitCnts)
        digitCnts = imutils.contours.sort_contours(digitCnts,
                                                   method="left-to-right")[0]
        digitText = []
        for digit in digitCnts:
            x, y, w, h = cv2.boundingRect(digit)
            if w > 6 and h > 12:
                ROI = stamina_image[y:y+h, x:x+w]
                sizedROI = cv2.resize(ROI, (57, 88))
                if train:
                    digitFeatures(sizedROI)
                else:

                    numberScore = []

                    for digitName, digitDICT in digits.items():
                        scores = []
                        for digitIteration, digitImage in digitDICT.items():
                            templateMatch = cv2.matchTemplate(
                                sizedROI, digitImage, cv2.TM_CCOEFF)
                            (_, score, _, _) = cv2.minMaxLoc(templateMatch)
                            scores.append(score)
                        avgScore = sum(scores)/len(scores)
                        numberScore.append((digitName, avgScore))
                    temp = sorted(
                        numberScore, key=lambda x: x[1], reverse=True)
                    digitText.append(temp[0][0])

        text = "".join(digitText)
        output[name] = text
    return output


def signatureItemFeatures(hero: np.array, templates: dict,
                          lvlRatioDict: dict = None):
    """
    Runs template matching SI identification against the 'hero' passed in.
        When lvlRatioDict is passed in the templates will be rescaled to
        attempt and find the best template size for detecting SI objects

    Args:
        hero: np.array(x,y.3) representing an rgb image
        templates: dictionary of information about each SI template to get ran
            against the image
        lvlRatioDict: dictionary that contains the predicted height of each
            signature item based on precomputed text to si scaling calculations
    Returns:
        dictionary with best "score" that each template achieved on the 'hero'
            image
    """
    x, y, _ = hero.shape
    # print(x, y)
    x_div = 2.4
    y_div = 2.0
    offset = 10
    hero_copy = hero.copy()

    hero = hero[0: int(y/y_div), 0: int(x/x_div)]

    # print("hero", hero.shape)

    si_dict = {}
    # baseSIDir = GV.siPath

    siFolders = os.listdir(GV.siBasePath)

    # imgCopy1 = newHero.copy()
    # grayCopy = cv2.cvtColor(imgCopy1, cv2.COLOR_BGR2GRAY)
    # count = 0
    for folder in siFolders:
        SIDir = os.path.join(GV.siBasePath, folder)
        SIPhotos = os.listdir(SIDir)
        if folder == "40":
            continue
        for imageName in SIPhotos:

            siImage = templates[folder]["image"]
            # siImage = cv2.imread(os.path.join(
            #     GV.siBasePath, folder, imageName))
            SIGray = cv2.cvtColor(siImage, cv2.COLOR_BGR2GRAY)

            templateImage = templates[folder].get(
                "crop", templates[folder].get("image"))
            mask = np.zeros_like(templateImage)

            if "morph" in templates[folder] and templates[folder]["morph"]:
                # print(folder, templates[folder])
                se = np.ones((2, 2), dtype='uint8')
                # inverted = cv2.bitwise_not(inverted)

                lower = np.array([0, 8, 0])
                upper = np.array([179, 255, 255])
                hsv = cv2.cvtColor(templateImage, cv2.COLOR_BGR2HSV)
                thresh = cv2.inRange(hsv, lower, upper)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, se)
                thresh = cv2.bitwise_not(thresh)

            else:
                templateGray = cv2.cvtColor(templateImage, cv2.COLOR_BGR2GRAY)

                thresh = cv2.threshold(
                    templateGray, 0, 255,
                    cv2.THRESH_OTSU + cv2.THRESH_BINARY)[1]
            inverted = cv2.bitwise_not(thresh)
            x, y = inverted.shape[:2]
            cv2.rectangle(inverted, (0, 0), (y, x), (255, 0, 0), 1)

            if folder == "0":
                pass
            else:
                inverted = cv2.bitwise_not(inverted)

            siCont = cv2.findContours(
                inverted, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            siCont = imutils.grab_contours(siCont)
            if folder == "0":
                # load.display_image(thresh, display=True)

                siCont = sorted(siCont, key=cv2.contourArea, reverse=True)[
                    1:templates[folder]["contourNum"]+1]
            else:
                siCont = sorted(siCont, key=cv2.contourArea, reverse=True)[
                    :templates[folder]["contourNum"]]

            # cv2.drawContours(mask, siCont, -1, (255, 255, 255))
            cv2.fillPoly(mask, siCont, [255, 255, 255])
            # load.display_image([mask, templateImage],
            #                    multiple=True, display=True)

            if folder not in si_dict:
                si_dict[folder] = {}
            si_dict[folder]["image"] = SIGray

            si_dict[folder]["template"] = templateImage

            si_dict[folder]["mask"] = mask
            # load.display_image(si_dict[folder]["mask"], display=True)

    numberScore = {}

    for folder_name, imageDict in si_dict.items():
        si_image = imageDict["template"]

        sourceSIImage = templates[folder_name]["image"]
        hero_h, hero_w = sourceSIImage.shape[:2]

        original_height, original_width = si_image.shape[:2]

        base_height_ratio = original_height/hero_h

        # resize_height
        base_new_height = round(lvlRatioDict[folder_name]["height"])
        new_height = round(base_new_height * base_height_ratio)
        scale_ratio = new_height/original_height
        new_width = round(original_width * scale_ratio)
        # print(folder_name, scale_ratio, base_new_height, base_height_ratio)
        # print(folder_name, original_height, original_width)

        # print(folder_name, new_height, new_width)
        # load.display_image(siImage)
        si_image = cv2.resize(
            si_image, (new_width, new_height))
        si_image_gray = cv2.cvtColor(si_image, cv2.COLOR_BGR2GRAY)
        hero_gray = cv2.cvtColor(hero, cv2.COLOR_BGR2GRAY)
        # load.display_image(siImage)
        mask = cv2.resize(
            imageDict["mask"], (new_width, new_height))
        mask_gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

        # siImage = imutils.resize(siImage, height=round(avg_height))
        # mask = imutils.resize(np.bitwise_not(
        #     imageDict["mask"]), height=round(avg_height))
        height, width = si_image.shape[:2]

        # print(folder_name, height, width)

        # sizedROI = cv2.resize(
        #     hero, (int(x * image_ratio), int(y * image_ratio)))
        # print(siImage.shape, imageDict["mask"].shape)
        if folder_name != "0":
            mask_gray = cv2.bitwise_not(mask_gray)
        # load.display_image(
        #     [si_image_gray, mask_gray], multiple=True, display=True)
        templateMatch = cv2.matchTemplate(
            hero_gray, si_image_gray, cv2.TM_CCOEFF_NORMED,
            mask=mask_gray)

        (_, score, _, scoreLoc) = cv2.minMaxLoc(templateMatch)
        scoreLoc
        coords = (scoreLoc[0] + width, scoreLoc[1] + height)

        cv2.rectangle(hero_copy, scoreLoc, coords, (255, 0, 0), 1)
        font = cv2.FONT_HERSHEY_SIMPLEX
        fontScale = 0.5
        color = (255, 0, 0)
        thickness = 2

        cv2.putText(
            hero_copy, folder_name, coords, font, fontScale, color, thickness,
            cv2.LINE_AA)

    #     top_left = max_loc
    # bottom_right = (top_left[0] + w, top_left[1] + h)

        # print(folderName, score)
        # print(siImage.shape, imageDict["mask"].shape)

        # load.display_image(
        #     [sizedROI, siImage], multiple=True,
        #     display=True)
        numberScore[folder_name] = score
    print(numberScore)

    load.display_image(hero_copy)

    return numberScore


def furnitureItemFeatures(hero: np.array, templates: dict,
                          lvlRatioDict: dict = None):
    """
    Runs template matching FI identification against the 'hero' passed in.
        When lvlRatioDict is passed in the templates will be rescaled to
        attempt and find the best template size for detecting FI objects

    Args:
        hero: np.array(x,y.3) representing an rgb image
        templates: dictionary of information about each FI template to get ran
            against the image
        lvlRatioDict: dictionary that contains the predicted height of each
            signature item based on precomputed text to si scaling calculations
    Returns:
        dictionary with best "score" that each template achieved on the 'hero'
            image
    """
    x, y, _ = hero.shape
    # print(x, y)
    x_div = 2.4
    y_div = 2.0
    x_offset = int(x*0.1)
    y_offset = int(y*0.35)
    hero_copy = hero.copy()

    hero = hero[y_offset: int(y*0.6), x_offset: int(x*0.35)]

    # print("hero", hero.shape)

    fi_dict = {}
    # baseSIDir = GV.siPath

    fi_folders = os.listdir(GV.fi_base_path)

    # imgCopy1 = newHero.copy()
    # grayCopy = cv2.cvtColor(imgCopy1, cv2.COLOR_BGR2GRAY)
    # count = 0
    for folder in fi_folders:
        fi_dir = os.path.join(GV.fi_base_path, folder)
        fi_photos = os.listdir(fi_dir)
        for image_name in fi_photos:
            fi_image = templates[folder]["image"]
            # fi_image = cv2.imread(os.path.join(
            #     GV.siBasePath, folder, image_name))
            template_image = templates[folder].get(
                "crop", templates[folder]["image"])
            mask = np.zeros_like(template_image)

            if "morph" in templates[folder] and templates[folder]["morph"]:
                # print(folder, templates[folder])
                se = np.ones((2, 2), dtype='uint8')
                # inverted = cv2.bitwise_not(inverted)

                lower = np.array([0, 8, 0])
                upper = np.array([179, 255, 255])
                hsv = cv2.cvtColor(template_image, cv2.COLOR_BGR2HSV)
                thresh = cv2.inRange(hsv, lower, upper)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, se)
                thresh = cv2.bitwise_not(thresh)

            else:
                template_gray = cv2.cvtColor(
                    template_image, cv2.COLOR_BGR2GRAY)

                thresh = cv2.threshold(
                    template_gray, 147, 255,
                    cv2.THRESH_BINARY)[1]
                inverted = thresh
            x, y = inverted.shape[:2]
            cv2.rectangle(inverted, (0, 0), (y, x), (255, 0, 0), 1)
            inverted = cv2.bitwise_not(inverted)

            fi_contours = cv2.findContours(
                inverted, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            fi_contours = imutils.grab_contours(fi_contours)
            # print(templates.keys())
            # print(templates[folder].keys())
            # print("cont num", folder, templates[folder]["contourNum"])
            fi_contours = sorted(fi_contours, key=cv2.contourArea,
                                 reverse=True)[:templates[
                                     folder]["contourNum"]]
            if folder == "3":
                master_contour = [
                    _cont for _cont_list in fi_contours for _cont in _cont_list]
                hull = cv2.convexHull(np.array(master_contour))
                # cv2.drawContours(mask, [hull], -1, (255, 255, 255))
                cv2.fillPoly(mask, [hull], [255, 255, 255])

            else:
                for _cont in fi_contours:
                    hull = cv2.convexHull(np.array(_cont))
                    # cv2.drawContours(mask, [hull], -1, (255, 255, 255))
                    cv2.fillPoly(mask, [hull], [255, 255, 255])

            if folder not in fi_dict:
                fi_dict[folder] = {}
            # si_dict[folder][imageName] = siImage
            fi_dict[folder]["template"] = template_image

            fi_dict[folder]["mask"] = mask
            # load.display_image(fi_dict[folder]["mask"], display=True)
            # load.display_image(template_image, display=True)
            # load.display_image(
            #     [template_image, fi_dict[folder]["mask"]], multiple=True, display=True)

            # fi_gray = cv2.cvtColor(fi_image, cv2.COLOR_BGR2GRAY)
            # fi_dict[folder]["image"] = fi_gray

    numberScore = {}

    for folder_name, imageDict in fi_dict.items():
        si_image = imageDict["template"]

        sourceSIImage = templates[folder_name]["image"]
        hero_h, hero_w = sourceSIImage.shape[:2]

        original_height, original_width = si_image.shape[:2]

        base_height_ratio = original_height/hero_h

        # resize_height
        base_new_height = round(lvlRatioDict[folder_name]["height"])
        new_height = round(base_new_height * base_height_ratio)
        scale_ratio = new_height/original_height
        new_width = round(original_width * scale_ratio)
        # print(folder_name, scale_ratio, base_new_height, base_height_ratio)
        # print(folder_name, original_height, original_width)

        # print(folder_name, new_height, new_width)
        # load.display_image(siImage)
        si_image = cv2.resize(
            si_image, (new_width, new_height))
        # si_image_gray = cv2.cvtColor(si_image, cv2.COLOR_BGR2GRAY)
        # hero_gray = cv2.cvtColor(hero, cv2.COLOR_BGR2GRAY)
        # load.display_image(siImage)
        mask = cv2.resize(
            imageDict["mask"], (new_width, new_height))
        mask_gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

        # siImage = imutils.resize(siImage, height=round(avg_height))
        # mask = imutils.resize(np.bitwise_not(
        #     imageDict["mask"]), height=round(avg_height))
        height, width = si_image.shape[:2]

        # print(folder_name, height, width)

        # sizedROI = cv2.resize(
        #     hero, (int(x * image_ratio), int(y * image_ratio)))
        # print(siImage.shape, imageDict["mask"].shape)
        # if folder_name != "0":
        #     mask_gray = cv2.bitwise_not(mask_gray)
        # load.display_image(
        #     [si_image_gray, mask_gray], multiple=True, display=True)
        # print("gray", hero_gray.shape)

        templateMatch = cv2.matchTemplate(
            hero, si_image, cv2.TM_CCOEFF_NORMED,
            mask=mask_gray)

        (_, score, _, scoreLoc) = cv2.minMaxLoc(templateMatch)
        scoreLoc = (scoreLoc[0] + x_offset, scoreLoc[1] + y_offset)
        coords = (scoreLoc[0] + width, scoreLoc[1] + height)

        cv2.rectangle(hero_copy, scoreLoc, coords, (255, 0, 0), 1)
        font = cv2.FONT_HERSHEY_SIMPLEX
        fontScale = 0.5
        color = (255, 0, 0)
        thickness = 2

        cv2.putText(
            hero_copy, folder_name, coords, font, fontScale, color, thickness,
            cv2.LINE_AA)

    #     top_left = max_loc
    # bottom_right = (top_left[0] + w, top_left[1] + h)

        # print(folderName, score)
        # print(siImage.shape, imageDict["mask"].shape)

        # load.display_image(
        #     [sizedROI, siImage], multiple=True,
        #     display=True)
        numberScore[folder_name] = score
    print(numberScore)

    load.display_image(hero_copy)

    return numberScore


# def getLevel(image: np.array, train=True):
#     # (hMin = 16 , sMin = 95, vMin = 129), (hMax = 27 , sMax = 138, vMax = 255)

#     digitFeatures(, baseDir)
#     if train:
#         result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
#         result = cv2.threshold(
#             result, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY)[1]

#         digitCnts = cv2.findContours(
#             mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#         digitCnts = imutils.grab_contours(digitCnts)
#         digitCnts = imutils.contours.sort_contours(digitCnts,
#                                                    method="left-to-right")[0]
#         digitText = []
#         for digit in digitCnts:
#             x, y, w, h = cv2.boundingRect(digit)
#             if w > 6 and h > 12:
#                 ROI = stamina_image[y:y+h, x:x+w]
#                 # sizedROI = cv2.resize(ROI, (57, 88))
#                 digitFeatures(ROI)


def digitFeatures(digit: np.array, saveDir=None):
    """
    Save a presized digit to whatever number is entered
    Args:
        digit: presized image of a digit, that will be saved as a training
            template under whatever digitName/label is entered when prompted
            by terminal
    Return:
        None
    """

    baseDir = GV.staminaTemplatesPath
    if saveDir:
        baseDir = saveDir
    digitFolders = os.listdir(baseDir)
    plt.figure()
    plt.imshow(digit)
    plt.ion()

    plt.show()

    number = input("Please enter the number shown in the image: ")

    plt.close()

    if number not in digitFolders:
        print("No such folder {}".format(number))
        number = "none"

    numberDir = os.path.join(baseDir, number)
    numberLen = str(len(os.listdir(numberDir)))
    numberName = os.path.join(numberDir, numberLen)

    cv2.imwrite("{}.png".format(numberName), digit)


if __name__ == "__main__":

    # Load in base truth/reference images
    files = load.findFiles("../hero_icon/*")
    baseImages = []
    for i in files:
        hero = cv2.imread(i)
        baseName = os.path.basename(i)
        name, ext = os.path.splitext(baseName)

        baseImages.append((name, hero))

    # load in screenshot of heroes
    stamina_image = cv2.imread("./stamina.jpg")
    heroesDict = processing.getHeroes(stamina_image)

    cropHeroes = load.crop_heroes(heroesDict)
    imageDB = load.build_flann(baseImages)

    for k, v in cropHeroes.items():

        name, baseHeroImage = imageDB.search(v, display=False)
        heroesDict[k]["label"] = name

    rows = generate_rows(heroesDict)
    staminaAreas = get_stamina_area(rows, heroesDict, stamina_image)
    staminaOutput = get_text(staminaAreas)
    output = {}

    for name, text in staminaOutput.items():
        label = heroesDict[name]["label"]
        if label not in output:
            output[label] = {}
        output[label]["stamina"] = text

    outputJson = json.dumps(output)
    print(outputJson)