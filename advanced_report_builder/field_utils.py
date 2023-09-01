from django_datatables.columns import ColumnNameError
from django_datatables.datatables import ColumnInitialisor

from advanced_report_builder.exceptions import ReportError


class ReportBuilderFieldUtils:
    column_initialisor_cls = ColumnInitialisor
    def get_field_details(self, base_model, field, report_builder_class, table=None, field_attr=None):

        if field_attr is None:
            field_attr = {}
        if isinstance(field, str) and field in report_builder_class.field_classes:
            field = report_builder_class.field_classes[field]

        path = field
        original_column_initialisor = self.column_initialisor_cls(start_model=base_model,
                                                                  path=field,
                                                                  table=table,
                                                                  **field_attr)

        try:
            columns = original_column_initialisor.get_columns()
        except ColumnNameError as e:
            raise ReportError(e)
        django_field = original_column_initialisor.django_field
        col_type_override = None
        if columns:
            col_type_override = columns[0]
            if isinstance(field, str) and '__' in field and col_type_override.model_path == '':
                # I think there is a bug in datatables where the model path isn't always set! hence the following code
                field_parts = field.split('__')[:-1]
                model_path = '__'.join(field_parts) + '__'
                col_type_override.model_path = model_path
                col_type_override.field = col_type_override.field  # actions the setter
                path = model_path

        if django_field is None and columns:
            col_type_override = columns[0]
            if isinstance(col_type_override.field, str):
                if isinstance(field, str):
                    path_parts = field.split('__')[:-1]
                    path_parts.append(col_type_override.field.split('__')[-1])
                    path = '__'.join(path_parts)
                    column_initialisor = self.column_initialisor_cls(start_model=base_model, path=path, table=table,
                                                                     **field_attr)
                    column_initialisor.get_columns()
                    django_field = column_initialisor.django_field
                else:
                    column_initialisor = self.column_initialisor_cls(start_model=base_model,
                                                                     path=col_type_override.field,
                                                                     table=table,
                                                                     **field_attr)
                    column_initialisor.get_columns()
                    django_field = column_initialisor.django_field

        return django_field, col_type_override, columns, path
