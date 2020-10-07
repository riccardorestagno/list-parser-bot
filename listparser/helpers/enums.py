from enum import Enum


class ArticleType(Enum):
    Business_Insider = 1
    BuzzFeed = 2
    CollegeHumor = 3
    Polygon = 4


def convert_enum_to_string(enum):
    return enum.name.replace("_", " ")


def convert_string_to_articletype_enum(string):
    return ArticleType[string.replace(" ", "_")]


def string_in_enum_list(enum_list, string):
    for enum in enum_list:
        if enum.name.replace("_", " ") == string.replace("_", " "):
            return True

    return False
