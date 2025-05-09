from django.dispatch import receiver

from advanced_report_builder.signals import model_report_save


@receiver(model_report_save)
def handle_report_save(sender, instance, created, user, **kwargs):
    if created:
        print("New report created:", instance)
    else:
        print("Report updated:", instance)