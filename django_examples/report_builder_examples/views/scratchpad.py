from django.db import connection, ProgrammingError
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.views import View
from report_builder_examples.models import Payment


class Scratchpad(View):

    def get(self, request):

        # p = Payment.objects.all()

        try:
            payment = Payment.objects.aggregate(
                a=((Sum('amount', filter=Q(received=False))+0.0) / Sum('amount') + 0.0) * 100
            )
        except ProgrammingError:
            payment = 'failed'

        q = connection.queries
        print(q)
        return HttpResponse(str(payment))
