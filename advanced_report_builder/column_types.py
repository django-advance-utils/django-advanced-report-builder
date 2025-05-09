from django.db import models
from django_datatables.columns import ColumnLink, CurrencyColumn, CurrencyPenceColumn

from advanced_report_builder.columns import (
    ColourColumn,
    ReverseForeignKeyBoolColumn,
    ReverseForeignKeyChoiceColumn,
    ReverseForeignKeyDateColumn,
    ReverseForeignKeyStrColumn,
)

NUMBER_FIELDS = (
    models.IntegerField,
    models.PositiveSmallIntegerField,
    models.PositiveIntegerField,
    models.FloatField,
)
DATE_FIELDS = (models.DateTimeField, models.DateField)
BOOLEAN_FIELD = models.BooleanField
CURRENCY_COLUMNS = (CurrencyColumn, CurrencyPenceColumn)
LINK_COLUMNS = ColumnLink
COLOUR_COLUMNS = ColourColumn
REVERSE_FOREIGN_KEY_STR_COLUMNS = ReverseForeignKeyStrColumn
REVERSE_FOREIGN_KEY_BOOL_COLUMNS = ReverseForeignKeyBoolColumn
REVERSE_FOREIGN_KEY_CHOICE_COLUMNS = ReverseForeignKeyChoiceColumn
REVERSE_FOREIGN_KEY_DATE_COLUMNS = ReverseForeignKeyDateColumn
