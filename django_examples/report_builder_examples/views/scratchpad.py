from django.db import connection, ProgrammingError
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.views import View
from report_builder_examples.models import Payment


class Scratchpad(View):

    def get(self, request):
        try:
            payment = Payment.objects.aggregate(
                a=(Coalesce((Sum('amount', filter=Q(received=False))+0.0), 0.0) / Coalesce(Sum('amount') + 0.0, 1.0)) * 100
            )
            #  SELECT ((sum(amount) filter(where received=false) + 0.0) /
            #  sum(amount) + 0.0) * 100  FROM report_builder_examples_payment
        except ProgrammingError:
            payment = 'failed'

        q = connection.queries
        print(q)
        return HttpResponse(str(payment))
