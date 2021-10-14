from django.db.models import CharField


class FieldTypes:
    FIELD_TYPE_STRING = 1
    FIELD_TYPE_NUMBER = 2
    FIELD_TYPE_DATE = 3
    FIELD_TYPE_BOOLEAN = 4
    FIELD_TYPE_MULTIPLE_CHOICE = 5
    FIELD_TYPE_FOREIGN_KEY = 6

    def get_operator(self, field_type):
        operators = {self.FIELD_TYPE_STRING: ['equal',
                                              'not_equal',
                                              'contains',
                                              'not_contains',
                                              'begins_with',
                                              'not_begins_with',
                                              'ends_with',
                                              'not_ends_with'
                                              ],
                     self.FIELD_TYPE_NUMBER: ['equal',
                                              'not_equal',
                                              'less',
                                              'less_or_equal',
                                              'greater',
                                              'greater_or_equal'
                                              ],
                     self.FIELD_TYPE_DATE: ['equal',
                                            'not_equal',
                                            'less',
                                            'less_or_equal',
                                            'greater',
                                            'greater_or_equal',
                                            'is_null',
                                            'is_not_null'
                                            ],
                     self.FIELD_TYPE_BOOLEAN: ['equal',
                                               'not_equal'
                                               ],
                     self.FIELD_TYPE_MULTIPLE_CHOICE: ['in',
                                                       'not_in'],
                     self.FIELD_TYPE_FOREIGN_KEY: ['is_null',
                                                   'is_not_null']
                     }
        return operators.get(field_type)

    def get_filter(self, query_builder_filters, model_field, field, title):
        if isinstance(model_field.field, CharField):
            query_builder_filters.append({"id": field,
                                          "label": title,
                                          "field": field,
                                          "type": "string",
                                          "operators": self.get_operator(self.FIELD_TYPE_STRING),
                                          "validation": {"allow_empty_value": True
                                                         }
                                          })
