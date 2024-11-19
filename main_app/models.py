from django.db import models
from django.urls import reverse
from accounts.models import User


class Site(models.Model):

    url = models.TextField(default="", unique=True)

    ping = models.IntegerField(null=True, blank=True, default="")


class Subscription(models.Model):

    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)

    site = models.ForeignKey(Site, on_delete=models.CASCADE)

    """name_field = models.CharField(
        db_column="name", max_length=200, blank=True, null=True,
    )

    subscribed = models.BooleanField(
        default=False, db_index=True
    )

    unsubscribed = models.BooleanField(
        default=False, db_index=True
    )

    def get_name(self):
        # need to update User db_model to have a name
        if self.user:
            return self.user
        return self.name_field
    
    def set_name(self, name):
        if not self.user:
            self.name_field = name
    name = property(get_name, set_name)

    email_field = models.EmailField(
        db_column="email", db_index=True, blank=True, null=True
    )

    def get_email(self):
        if self.user:
            return self.user.email
        return self.email_field
    
    def set_email(self, email):
        if not self.user:
            self.email_field = email
    email = property(get_email, set_email)"""

    def update(self, action):

        assert action in ("subscribe", "update", "unsubscribe")

        if action == "subscribe" or action == "update":
            self.subscribed = True
        else:
            self.unsubscribed = True

        self.save()

    def _subscribe(self):

        self.subscribed = True
        self.unsubscribed = False

    def _unsubscribe(self):

        self.subscribed = False
        self.unsubscribed = True

    def save(self, *args, **kwargs):

        assert self.user or self.email_field

        if self.pk:
            assert(Subscription.objects.filter(pk=self.pk).count() == 1)

            subsription = Subscription.objects.get(pk=self.pk)
            old_subscribed = subsription.subscribed
            old_unsubscribed = subsription.unsubscribed

            if ((self.subscribed and not old_subscribed) or
                (old_unsubscribed and not self.unsubscribed)):
                self._subscribe()

                assert not self.unsubscribed
                assert self.subscribed

            elif ((self.unsubscribed and not old_unsubscribed) or
                  (old_subscribed and not self.subscribed)):
                self._unsubscribe()

                assert not self.subscribed
                assert self.unsubscribed

        else:
            if self.subscribed:
                self._subscribe()
            elif self.unsubscribed:
                self._unsubscribe()

        super().save(*args, **kwargs)

    def __str__(self):
        if self.name:
            return "%(name)s <%(email)s> to %(site)s" % {
                'name': self.name,
                'email': self.email,
                'site': self.site
            }
        
        else:
            return "%(email)s to %(site)s" % {
                'email': self.email,
                'site': self.site
            }
    
    def subscribe_activate_url(self):
        return reverse('subscription_update', kwargs={
            'site_slug': self.site.slug,
            'email': self.email,
            'action': 'subscribe'
        })
    
    def unsubscribe_activate_url(self):
        return reverse('subscription_update', kwargs={
            'site_slug': self.site.slug,
            'email': self.email,
            'action': 'unsubscribe'
        })
    
    def update_activate_url(self):
        return reverse('subscription_update', kwargs={
            'site_slug': self.site.slug,
            'email': self.email,
            'action': 'update'
        })