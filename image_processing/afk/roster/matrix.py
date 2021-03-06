"""
A Module that contains all features and implementations that pertain to the
Matrix Class

The Matrix Class is used to Store a List of Row instance that in turn stores a
list of RowItems essentially making the Matrix class a 2 Dimensional Array that
provides extra features when interacting with groups of Row Objects
"""
from typing import Callable

import numpy as np

import image_processing.globals as GV
import image_processing.afk.roster.column_objects as CO
import image_processing.afk.roster.row as RO

from image_processing.afk.roster.dimensions_object import DimensionsObject
from image_processing.processing.types.types import SegmentRectangle


class Matrix():
    # pylint: disable=protected-access
    """
    A matrix Object used to store two dimensional objects that tracks
        row, columns object size and more
    """

    def __init__(self, source_height: int, source_width: int,
                 spacing_percent: int = 0.5):
        """
        Create matrix object to track list of image_processing.stamina.row

        Args:
            source_height: maximum height of source
            source_width: maximum width of source
            spacing_percent(int): percent that a new object must be overlapping
                with an existing row to get added to that row
                (ex. 0.5 = 50% overlap)
        """
        self.source_height = source_height
        self.source_width = source_width
        self._heads: dict[int, Callable[[], int]] = {}
        self._row_list: list[RO.Row] = []
        self._idx = 0
        self.spacing_percent = spacing_percent
        self.columns = CO.ColumnObjects(self)

    def __str__(self):
        return "\n".join([str(row_item) for row_item in self._row_list])

    def __iter__(self):
        """
        Return self
        """
        return self

    def __next__(self):
        """
        Iterate over all rows in self._row_list
        """
        self._idx += 1
        try:
            return self._row_list[self._idx - 1]
        except IndexError:
            self._idx = 0
            raise StopIteration  # pylint: disable=raise-missing-from

    def __len__(self):
        return len(self._row_list)

    def __getitem__(self, index: int):
        """
        Get a row by its index
        Args:
            index: position of row in matrix

        Returns:
            image_processing.stamina.row
        """
        return self._row_list[index]

    def get_avg_width(self) -> int:
        """
        Return the average width of RowItems in the matrix
        """
        # avg_width = [_row.avg_width for _row in self._row_list]
        # print(np.mean(avg_width))
        avg_width_list = [_row.get_average() for _row in self._row_list]
        return np.mean(avg_width_list)

    def get_avg_height(self):
        """
        Return the average height of RowItems in the matrix
        """
        avg_height = [row._get_avg_height() for row in self._row_list]
        return np.mean(avg_height)

    def get_avg_row_gap(self):
        """
        Get the average width gap between RowItems in each row

        Return:
            Average width gap(int) between RowItems when matrix contains rows

            Otherwise returns (None)
        """
        gap_list: list[int] = []
        for _row in self._row_list:
            _temp_gap = _row._get_item_gap()
            if _temp_gap is not None:
                gap_list.append(_temp_gap)
        avg_gap = np.mean(gap_list)
        if avg_gap == 0:
            return None
        else:
            return avg_gap

    def auto_append(self, dimensions: SegmentRectangle, name: str,
                    detect_collision: bool = True,
                    dimension_object=False):
        """
        Add a new entry into the matrix, either creating a new row or adding to
            an existing row depending on `spacing` settings and distance.
        Args:
            dimensions: x,y,width,height of object
            name: identifier for object
            detect_collision: check for object overlap/collisions when
                appending to row
            dimension_object: flag to treat `dimensions` as DimensionObject
                instead of a tuple
        Return:
            None
        """
        if dimension_object:
            _temp_dimensions = dimensions
        else:
            _temp_dimensions = DimensionsObject(dimensions)
        y_coord = _temp_dimensions.y
        _row_index = None
        for _index, _head in self._heads.items():
            # If there are no close rows set flag to create new row
            average_row_height = self._row_list[_index]._get_avg_height()
            row_end = (_head() + average_row_height)
            object_end = (y_coord + _temp_dimensions.height)
            object_end_difference = abs(row_end - object_end)
            # find overlap percentage
            overlap_percentage = (1 - (object_end_difference/average_row_height))
            if (overlap_percentage >  self.spacing_percent):
                _row_index = _index
                break
        if _row_index is not None:
            self._row_list[_row_index].append(
                dimensions, name, detect_collision=detect_collision)
        else:
            _temp_row = RO.Row(self.columns)
            _temp_row.append(dimensions, name,
                             detect_collision=detect_collision)
            self._heads[len(self._row_list)] = _temp_row.get_head
            self._row_list.append(_temp_row)

    def sort(self):
        """
        Sort Matrix by y coordinate of each row
        """
        for _row in self._row_list:
            _row.sort()
        self._row_list.sort(key=lambda _row: _row.head)

    def prune(self, threshold: int, fill_hero: bool = True,
              hard_threshold: int = 1):
        """
        Remove all rows that have a length less than the `threshold`

        Args:
            threshold: limit that determines if a row should be pruned when
                its length is less than this
            fill_hero: flag to attempt to fill missing hero locations in each
                row that is below the threshold
            hard_threshold: number that will trigger a row removal regardless
                of if fill_hero is set to true
        Return:
            None
        """
        self._balance()
        _prune_list = []

        for _index, _row_object in enumerate(self._row_list):
            if len(_row_object) < threshold and _index != (
                    len(self._row_list) - 1):
                if fill_hero and len(_row_object) > hard_threshold:
                    # print("before: {}".format(_row_object))
                    _column_index = 0
                    while _column_index < len(self.columns.columns):
                        columns = [self.columns.find_column(
                            _row_item) for _row_item in _row_object]
                        # print(_column_index, columns,
                        #       len(self.columns.columns))
                        if _column_index not in columns:
                            # print("{} not in {}".format(
                            #     _column_index, columns))
                            right_side = [
                                _i for _i in columns if _i > _column_index]
                            left_side = [
                                _i for _i in columns if _i < _column_index]
                            right_side.sort()
                            left_side.sort()
                            if len(left_side) > 0:
                                closest_left = left_side[-1]
                            else:
                                closest_left = None
                            if len(right_side) > 0:
                                closest_right = right_side[0]
                            else:
                                closest_right = None
                            if closest_left and closest_right:
                                # print("mid")
                                left_row_object = self.columns.columns[
                                    closest_left]
                                right_row_object = self.columns.columns[
                                    closest_right]
                                left_x = left_row_object.x2
                                right_x = right_row_object.x
                                # print("x1: {} x2: {}".format(
                                # left_x, right_x))
                                gap_size = right_x - left_x
                                _avg_width = self.get_avg_width()
                                # print(gap_size, _avg_width)
                                raw_missing_row_items = gap_size/_avg_width
                                missing_row_items = round(
                                    raw_missing_row_items)

                                # print(missing_row_items, gap_size/_avg_width)
                                # print("num missing:{} gap:{} item_w:{}"
                                # .format(
                                #     missing_row_items, gap_size, _avg_width))

                                extra_gap = gap_size - \
                                    (missing_row_items*_avg_width)
                                extra_gap_number = (missing_row_items + 1)
                                extra_gap_width = extra_gap/extra_gap_number

                                _avg_height = self.get_avg_height()

                                for _itr in range(missing_row_items):
                                    _temp_dims = SegmentRectangle(
                                        left_x + extra_gap_width,
                                        _row_object._get_row_bottom() - _avg_height,
                                        _avg_width,
                                        _avg_height)
                                    _temp_dim_object = DimensionsObject(
                                        _temp_dims)
                                    left_x = _temp_dim_object.x2
                                    _row_object.append(
                                        _temp_dim_object,
                                        detect_collision=False)

                            elif closest_left:
                                _avg_height = self.get_avg_height()
                                _avg_width = self.get_avg_width()

                                left_row_object = self.columns.columns[
                                    closest_left]

                                _avg_gap = self.get_avg_row_gap()
                                left_x = left_row_object.x2
                                gap_size = self.source_width - left_x
                                _leftover_gap = gap_size

                                while _leftover_gap > _avg_width:
                                    _temp_dims = SegmentRectangle(
                                        left_x + _avg_gap,
                                        _row_object._get_row_bottom(
                                        ) - _avg_height,
                                        _avg_width, _avg_height)
                                    _temp_dim_object = DimensionsObject(
                                        _temp_dims)
                                    left_x = _temp_dim_object.x2
                                    _row_object.append(_temp_dim_object)
                                    _leftover_gap -= (_avg_width + _avg_gap)

                            elif closest_right:
                                # print(closest_right)
                                right_row_object = self.columns.columns[
                                    closest_right]

                                right_x = right_row_object.x
                                gap_size = right_x

                                _avg_height = self.get_avg_height()
                                _avg_width = self.get_avg_width()
                                _avg_gap = self.get_avg_row_gap()

                                _leftover_gap = gap_size
                                while _leftover_gap > _avg_width:
                                    _temp_dims = SegmentRectangle(
                                        right_x - _avg_width,
                                        _row_object._get_row_bottom(
                                        ) - _avg_height,
                                        _avg_width, _avg_height)

                                    _temp_dim_object = DimensionsObject(
                                        _temp_dims)
                                    right_x = _temp_dim_object.x
                                    _row_object.append(_temp_dim_object)
                                    _leftover_gap -= (_avg_width + _avg_gap)

                        _column_index += 1
                    # print("after: {}".format(_row_object))
                else:
                    _prune_list.append(_index)
            _row_object.sort()
        if len(_prune_list) > 0:
            if GV.verbosity(1):
                print(f"Deleting ({len(_prune_list)}) "
                      f"row objects({_prune_list}) from matrix. Ensure that "
                      "get_heroes was successful")
            for _index in sorted(_prune_list, reverse=True):
                if GV.verbosity(1):
                    print(f"Deleted row object ({self._row_list[_index]}) of "
                          f"len ({len(self._row_list[_index])})")
                self._row_list.pop(_index)
                del self._heads[_index]

    def _balance(self, width_diff_threshold=0.1,
                 height_diff_threshold=0.1):
        """
        Balance self.columns object so all columns that are adjacent have
            equal width, additionally iterate through matrix object and adjust
            any Row_items that fall outside columns
        """
        self.columns.balance()
        avg_w = self.get_avg_width()
        avg_h = self.get_avg_height()
        width_diff = width_diff_threshold*avg_w
        height_diff = height_diff_threshold*avg_h

        adjusted_avg_w = avg_w + width_diff
        adjusted_avg_h = avg_h + height_diff

        for _row in self._row_list:
            _row_bottom = _row._get_row_bottom()
            _row_top = _row_bottom - avg_h
            _adjusted_row_top = _row_bottom - adjusted_avg_h

            for _row_item in _row:
                # _row_item.dimensions._display(GV.IMAGE_SS, display=True)
                _index = self.columns.find_column(_row_item)
                _column = self.columns[_index]
                if _row_item.dimensions.x < _column.x:
                    # print("x edit", _row_item.dimensions.x, _column.x)
                    _row_item.dimensions.x = max(
                        _row_item.dimensions.x, _column.x)
                if _row_item.dimensions.x2 > _column.x2:
                    # print("x2 edit", _row_item.dimensions.x2, _column.x2)
                    _row_item.dimensions.x2 = min(
                        _row_item.dimensions.x2, _column.x2)
                if _row_item.dimensions.y > _adjusted_row_top:
                    # print("y edit", _row_item.dimensions.y, _row_top)
                    _row_item.dimensions.y = _row_top

                if _row_item.dimensions.y2 < (_row_bottom *
                                              (1 + height_diff_threshold)):
                    # print("y2 edit", _row_item.dimensions.y2, _row_bottom)
                    _row_item.dimensions.y2 = _row_bottom

                if (abs(_row_item.dimensions.width
                        - adjusted_avg_w) > (width_diff) or
                        _row_item.dimensions.width -
                        _row_item.dimensions.height > width_diff):
                    _row_item.dimensions.x = max(
                        _row_item.dimensions.x, _column.x)
                    _row_item.dimensions.x2 = _row_item.dimensions.x + avg_w
                if (abs(_row_item.dimensions.height
                        - adjusted_avg_h) > height_diff or
                        _row_item.dimensions.height -
                        _row_item.dimensions.width > height_diff):
                    _row_item.dimensions.y = max(
                        _row_item.dimensions.y,
                        (_row_bottom - avg_h))
                    _row_item.dimensions.y2 = _row_item.dimensions.y + avg_h
                # print(self.columns)
                # _row_item.dimensions._display(GV.IMAGE_SS, display=True)
                # self.columns._display(GV.IMAGE_SS, display=True)
