from django.apps import apps
from django_datatables.columns import ColumnNameError
from django_datatables.datatables import ColumnInitialisor

from advanced_report_builder.column_types import (
    COLOUR_COLUMNS,
    DATE_FIELDS,
    LINK_COLUMNS,
    NUMBER_FIELDS,
)
from advanced_report_builder.exceptions import ReportError
from advanced_report_builder.utils import get_report_builder_class


class ReportBuilderFieldUtils:
    column_initialisor_cls = ColumnInitialisor

    def get_field_details(self, base_model, field, report_builder_class, table=None, field_attr=None):
        if field_attr is None:
            field_attr = {}
        if isinstance(field, str) and field in report_builder_class.field_classes:
            field = report_builder_class.field_classes[field]

        path = field
        original_column_initialisor = self.column_initialisor_cls(
            start_model=base_model, path=field, table=table, **field_attr
        )

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
                    column_initialisor = self.column_initialisor_cls(
                        start_model=base_model, path=path, table=table, **field_attr
                    )
                    column_initialisor.get_columns()
                    django_field = column_initialisor.django_field
                else:
                    column_initialisor = self.column_initialisor_cls(
                        start_model=base_model,
                        path=col_type_override.field,
                        table=table,
                        **field_attr,
                    )
                    column_initialisor.get_columns()
                    django_field = column_initialisor.django_field

        return django_field, col_type_override, columns, path

    def get_field_display_value(
        self,
        field_type,
        fields_values,
        base_model,
        report_builder_class,
        selected_field_value,
        for_select2=False,
    ):
        if field_type == 'date':
            self._get_date_fields(
                base_model=base_model,
                fields=fields_values,
                report_builder_class=report_builder_class,
                selected_field_id=selected_field_value,
            )
        elif field_type == 'link':
            self._get_column_link_fields(
                base_model=base_model,
                fields=fields_values,
                report_builder_class=report_builder_class,
                selected_field_id=selected_field_value,
            )
        elif field_type == 'number':
            self._get_number_fields(
                base_model=base_model,
                fields=fields_values,
                report_builder_class=report_builder_class,
                selected_field_id=selected_field_value,
            )
        elif field_type == 'colour':
            self._get_colour_fields(
                base_model=base_model,
                fields=fields_values,
                report_builder_class=report_builder_class,
                selected_field_id=selected_field_value,
            )
        elif field_type == 'all':
            self._get_fields(
                base_model=base_model,
                fields=fields_values,
                report_builder_class=report_builder_class,
                selected_field_id=selected_field_value,
                for_select2=for_select2,
            )
        elif field_type == 'order' or field_type == 'django_order':
            self._get_fields(
                base_model=base_model,
                fields=fields_values,
                report_builder_class=report_builder_class,
                selected_field_id=selected_field_value,
                for_select2=for_select2,
                show_order_by_fields=True,
            )

    def _get_date_fields(
        self,
        base_model,
        fields,
        report_builder_class,
        selected_field_id=None,
        search_string=None,
    ):
        return self._get_fields(
            base_model=base_model,
            fields=fields,
            report_builder_class=report_builder_class,
            selected_field_id=selected_field_id,
            field_types=DATE_FIELDS,
            for_select2=True,
            allow_annotations_fields=False,
            search_string=search_string,
        )

    def _get_number_fields(
        self,
        base_model,
        fields,
        report_builder_class,
        selected_field_id=None,
        search_string=None,
    ):
        return self._get_fields(
            base_model=base_model,
            fields=fields,
            report_builder_class=report_builder_class,
            selected_field_id=selected_field_id,
            field_types=NUMBER_FIELDS,
            for_select2=True,
            search_string=search_string,
        )

    def _get_column_link_fields(
        self,
        base_model,
        fields,
        report_builder_class,
        selected_field_id=None,
        search_string=None,
    ):
        return self._get_fields(
            base_model=base_model,
            fields=fields,
            report_builder_class=report_builder_class,
            selected_field_id=selected_field_id,
            column_types=LINK_COLUMNS,
            for_select2=True,
            search_string=search_string,
            allow_annotations_fields=False,
        )

    def _get_colour_fields(
        self,
        base_model,
        fields,
        report_builder_class,
        selected_field_id=None,
        search_string=None,
    ):
        return self._get_fields(
            base_model=base_model,
            fields=fields,
            report_builder_class=report_builder_class,
            selected_field_id=selected_field_id,
            column_types=COLOUR_COLUMNS,
            for_select2=True,
            search_string=search_string,
            allow_annotations_fields=False,
        )

    def _get_fields(
        self,
        base_model,
        fields,
        report_builder_class,
        tables=None,
        prefix='',
        title_prefix='',
        title=None,
        colour=None,
        previous_base_model=None,
        selected_field_id=None,
        for_select2=False,
        pivot_fields=None,
        allow_annotations_fields=True,
        field_types=None,
        column_types=None,
        search_string=None,
        show_order_by_fields=False,
        extra_fields=None,
        must_have_django_field=False,
        allow_pivots=True,
        include_mathematical_columns=False,
    ):
        if title is None:
            title = report_builder_class.title
        if colour is None:
            colour = report_builder_class.colour

        if tables is not None:
            tables.append({'name': title, 'colour': colour})

        report_builder_class_fields = report_builder_class.fields

        if extra_fields:
            report_builder_class_fields += extra_fields

        for report_builder_field in report_builder_class_fields:
            if (
                not isinstance(report_builder_field, str)
                or report_builder_field not in report_builder_class.exclude_display_fields
                or (show_order_by_fields and report_builder_field in report_builder_class.order_by_fields)
            ):
                django_field, col_type_override, columns, _ = self.get_field_details(
                    base_model=base_model,
                    field=report_builder_field,
                    report_builder_class=report_builder_class,
                )
                if django_field is None and must_have_django_field:
                    continue
                for column in columns:
                    if (
                        (field_types is None and column_types is None)
                        or (field_types is not None and isinstance(django_field, field_types))
                        or (column_types is not None and isinstance(col_type_override, column_types))
                        or (allow_annotations_fields and column.annotations)
                    ):
                        full_id = prefix + column.column_name
                        if selected_field_id is None or selected_field_id == full_id:
                            if column.title == '':
                                full_title = title_prefix + col_type_override.title_from_name(column.column_name)
                            else:
                                full_title = title_prefix + column.title
                            if self._is_search_match(search_string=search_string, title=full_title):
                                if for_select2:
                                    fields.append({'id': full_id, 'text': full_title})
                                else:
                                    fields.append(
                                        {
                                            'field': full_id,
                                            'label': full_title,
                                            'colour': colour,
                                        }
                                    )

        if allow_pivots and not for_select2 and pivot_fields is not None:
            for pivot_code, pivot_field in report_builder_class.pivot_fields.items():
                full_id = prefix + pivot_code
                full_title = title_prefix + pivot_field['title']
                if self._is_search_match(search_string=search_string, title=full_title):
                    pivot_fields.append(
                        {
                            'field': full_id,
                            'label': title_prefix + pivot_field['title'],
                            'colour': colour,
                        }
                    )

        for include_field, include in report_builder_class.includes.items():
            app_label, model, report_builder_fields_str = include['model'].split('.')
            local_allow_pivots = allow_pivots
            if local_allow_pivots and not include.get('allow_pivots', True):
                local_allow_pivots = False

            new_model = apps.get_model(app_label, model)
            if new_model != previous_base_model:
                new_report_builder_class = get_report_builder_class(
                    model=new_model, class_name=report_builder_fields_str
                )
                self._get_fields(
                    base_model=new_model,
                    fields=fields,
                    report_builder_class=new_report_builder_class,
                    tables=tables,
                    prefix=f'{prefix}{include_field}__',
                    title_prefix=f'{title_prefix}{include["title"]} -> ',
                    title=include.get('title'),
                    colour=include.get('colour'),
                    previous_base_model=base_model,
                    selected_field_id=selected_field_id,
                    for_select2=for_select2,
                    pivot_fields=pivot_fields,
                    allow_annotations_fields=allow_annotations_fields,
                    field_types=field_types,
                    column_types=column_types,
                    search_string=search_string,
                    show_order_by_fields=show_order_by_fields,
                    allow_pivots=local_allow_pivots,
                )

        if include_mathematical_columns:
            fields.extend(
                [
                    {
                        'colour': '#D4AF37',
                        'field': 'rb_addition',
                        'label': 'Maths: Addition Field',
                    },
                    {
                        'colour': '#D4AF37',
                        'field': 'rb_subtraction',
                        'label': 'Maths: Subtraction Field',
                    },
                    {
                        'colour': '#D4AF37',
                        'field': 'rb_times',
                        'label': 'Maths: Times Field',
                    },
                    {
                        'colour': '#D4AF37',
                        'field': 'rb_division',
                        'label': 'Maths: Division Field',
                    },
                    {
                        'colour': '#D4AF37',
                        'field': 'rb_percentage',
                        'label': 'Maths: Percentage Field',
                    },
                ]
            )

    @staticmethod
    def _is_search_match(search_string, title):
        if search_string is None:
            return True
        return search_string.lower() in title.lower()
