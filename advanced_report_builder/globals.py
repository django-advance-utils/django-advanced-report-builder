from django.db import models
from django.db.models import Sum, Max, Min, Count, Avg
from django.db.models.functions import TruncMonth, TruncQuarter, TruncYear, TruncWeek, TruncDay

NUMBER_FIELDS = (models.IntegerField, models.PositiveSmallIntegerField, models.PositiveIntegerField)
DATE_FIELDS = (models.DateTimeField, models.DateField)

ANNOTATION_VALUE_CHOICES = (('', ''),
                            ('y', 'Year'),
                            ('q', 'Quarter'),
                            ('m', 'Month'),
                            ('w', 'Week'),
                            ('d', 'Day'))

ANNOTATION_VALUE_FUNCTIONS = {'y': TruncYear,
                              'q': TruncQuarter,
                              'm': TruncMonth,
                              'w': TruncWeek,
                              'd': TruncDay}

ANNOTATIONS_CHOICES = (('', ''),
                       ('sum', 'Sum'),
                       ('max', 'Max'),
                       ('min', 'Min'),
                       ('count', 'Count'),
                       ('avg', 'Avg'))

ANNOTATION_FUNCTIONS = {'sum': Sum,
                        'max': Max,
                        'min': Min,
                        'count': Count,
                        'avg': Avg}

DATE_FORMAT_TYPE_DD_MM_YY_SLASH = 1
DATE_FORMAT_TYPE_DD_MM_YYYY_SLASH = 2
DATE_FORMAT_TYPE_MM_DD_YY_SLASH = 3
DATE_FORMAT_TYPE_MM_DD_YYYY_SLASH = 4
DATE_FORMAT_TYPE_DD_MM_YY_DASH = 5
DATE_FORMAT_TYPE_DD_MM_YYYY_DASH = 6
DATE_FORMAT_TYPE_MM_DD_YY_DASH = 7
DATE_FORMAT_TYPE_MM_DD_YYYY_DASH = 8
DATE_FORMAT_TYPE_WORDS_MM_DD_YYYY = 9
DATE_FORMAT_TYPE_WORDS_DD_MM_YYYY = 10
DATE_FORMAT_TYPE_SHORT_WORDS_MM_DD_YYYY = 11
DATE_FORMAT_TYPE_SHORT_WORDS_DD_MM_YYYY = 12
DATE_FORMAT_TYPE_YYYY = 13
DATE_FORMAT_TYPE_YY = 14
DATE_FORMAT_TYPE_MM_YY = 15
DATE_FORMAT_TYPE_MM_YYYY = 16
DATE_FORMAT_TYPE_WORDS_MM_YY = 17
DATE_FORMAT_TYPE_WORDS_MM_YYYY = 18
DATE_FORMAT_TYPE_SHORT_WORDS_MM_YY = 19
DATE_FORMAT_TYPE_SHORT_WORDS_MM_YYYY = 20
DATE_FORMAT_TYPE_MM = 21
DATE_FORMAT_TYPE_WORDS_MM = 22
DATE_FORMAT_TYPE_SHORT_WORDS_MM = 23
DATE_FORMAT_TYPE_WW = 24
DATE_FORMAT_TYPE_WW_YYYY_DASH = 25
DATE_FORMAT_TYPE_WW_YY_DASH = 26


DATE_FORMAT_TYPES_DJANGO_FORMAT = {DATE_FORMAT_TYPE_DD_MM_YY_SLASH: '%d/%m/%y',
                                   DATE_FORMAT_TYPE_DD_MM_YYYY_SLASH: '%d/%m/%Y',
                                   DATE_FORMAT_TYPE_MM_DD_YY_SLASH: '%m/%d/%y',
                                   DATE_FORMAT_TYPE_MM_DD_YYYY_SLASH: '%m/%d/%Y',
                                   DATE_FORMAT_TYPE_DD_MM_YY_DASH: '%d-%m-%y',
                                   DATE_FORMAT_TYPE_DD_MM_YYYY_DASH: '%d-%m-%Y',
                                   DATE_FORMAT_TYPE_MM_DD_YY_DASH: '%m-%d-%y',
                                   DATE_FORMAT_TYPE_MM_DD_YYYY_DASH: '%m-%d-%Y',
                                   DATE_FORMAT_TYPE_WORDS_MM_DD_YYYY: '%B %d %Y',
                                   DATE_FORMAT_TYPE_WORDS_DD_MM_YYYY: '%d %B %Y',
                                   DATE_FORMAT_TYPE_SHORT_WORDS_MM_DD_YYYY: '%b %d %Y',
                                   DATE_FORMAT_TYPE_SHORT_WORDS_DD_MM_YYYY: '%d %b %Y',
                                   DATE_FORMAT_TYPE_YYYY: '%Y',
                                   DATE_FORMAT_TYPE_YY: '%y',
                                   DATE_FORMAT_TYPE_MM_YY: '%m %y',
                                   DATE_FORMAT_TYPE_MM_YYYY: '%m %Y',
                                   DATE_FORMAT_TYPE_WORDS_MM_YY: '%B %y',
                                   DATE_FORMAT_TYPE_WORDS_MM_YYYY: '%B %Y',
                                   DATE_FORMAT_TYPE_SHORT_WORDS_MM_YY: '%b %y',
                                   DATE_FORMAT_TYPE_SHORT_WORDS_MM_YYYY: '%b %Y',
                                   DATE_FORMAT_TYPE_MM: '%m',
                                   DATE_FORMAT_TYPE_WORDS_MM: '%B',
                                   DATE_FORMAT_TYPE_SHORT_WORDS_MM: '%b',
                                   DATE_FORMAT_TYPE_WW: '%W',
                                   DATE_FORMAT_TYPE_WW_YYYY_DASH: '%W-%Y',
                                   DATE_FORMAT_TYPE_WW_YY_DASH: '%W-%y',

                                   }

DATE_FORMAT_TYPES = (
    ('', ''),
    (DATE_FORMAT_TYPE_DD_MM_YY_SLASH, 'dd/mm/yy'),
    (DATE_FORMAT_TYPE_DD_MM_YYYY_SLASH, 'dd/mm/yyyy'),
    (DATE_FORMAT_TYPE_MM_DD_YY_SLASH, 'mm/dd/yy'),
    (DATE_FORMAT_TYPE_MM_DD_YYYY_SLASH, 'mm/dd/yyyy'),
    (DATE_FORMAT_TYPE_DD_MM_YY_DASH, 'dd-mm-yy'),
    (DATE_FORMAT_TYPE_DD_MM_YYYY_DASH, 'dd-mm-yyyy'),
    (DATE_FORMAT_TYPE_MM_DD_YY_DASH, 'mm-dd-yy'),
    (DATE_FORMAT_TYPE_MM_DD_YYYY_DASH, 'mm-dd-yyyy'),
    (DATE_FORMAT_TYPE_WORDS_MM_DD_YYYY, 'MM d yyyy'),
    (DATE_FORMAT_TYPE_WORDS_DD_MM_YYYY, 'd MM yyyy'),
    (DATE_FORMAT_TYPE_SHORT_WORDS_MM_DD_YYYY, 'M d yyyy'),
    (DATE_FORMAT_TYPE_SHORT_WORDS_DD_MM_YYYY, 'd M yyyy'),
    (DATE_FORMAT_TYPE_YYYY, 'yyyy'),
    (DATE_FORMAT_TYPE_YY, 'yy'),
    (DATE_FORMAT_TYPE_MM_YY, 'mm yy'),
    (DATE_FORMAT_TYPE_MM_YYYY, 'mm yyyy'),
    (DATE_FORMAT_TYPE_WORDS_MM_YY, 'MM yy'),
    (DATE_FORMAT_TYPE_WORDS_MM_YYYY, 'MM yyyy'),
    (DATE_FORMAT_TYPE_SHORT_WORDS_MM_YY, 'b yy'),
    (DATE_FORMAT_TYPE_SHORT_WORDS_MM_YYYY, 'b yyyy'),
    (DATE_FORMAT_TYPE_MM, 'mm'),
    (DATE_FORMAT_TYPE_WORDS_MM, 'MM'),
    (DATE_FORMAT_TYPE_SHORT_WORDS_MM, 'd'),
    (DATE_FORMAT_TYPE_WW, 'WW'),
    (DATE_FORMAT_TYPE_WW_YYYY_DASH, 'WW-YYYY'),
    (DATE_FORMAT_TYPE_WW_YY_DASH, 'WW-YY'),
)
