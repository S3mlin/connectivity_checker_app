import asyncio
import os
from helper_functions.checker import check_subscribed_sites_async
from celery import shared_task
from accounts.models import User
from main_app.models import Subscription
from django.core import mail
from asgiref.sync import sync_to_async


@sync_to_async
def fetch_users_with_subscriptions():
    return User.objects.filter(subscription__isnull=False).distinct()

@sync_to_async
def fetch_subscribed_sites(user):
    return Subscription.objects.filter(user=user).values_list('site', flat=True)

@shared_task
def check_sites_and_send_mail():
    sender=os.getenv("EMAIL_HOST_USER")
    asyncio.run(check_subscribed_sites_async())
    users_with_subscriptions = User.objects.filter(subscription__isnull=False).distinct()
    emails = []
    subject = "Connectivity Check Results"
    for user in users_with_subscriptions:
        subscribed_sites = Subscription.objects.filter(user=user).select_related('site')
        email_text = (
            f"Hello {user.email},\n\n"
            "Here are the ping results for your subscribed sites:\n\n"
            + "\n".join([f"{site.site.url}: {site.site.ping*100}ms" for site in subscribed_sites])
            + "\n\nBest regards,\nConnectivity Checker App"
        )
        email = [subject, email_text, sender, [user.email]]
        emails.append(email)
    results = mail.send_mass_mail(emails)
    return results
