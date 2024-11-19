from django import forms
from main_app.models import Site, Subscription


class SiteForm(forms.models.ModelForm):

    class Meta:
        model = Site
        fields = ("url",)
        widgets = {
            "url": forms.widgets.TextInput(
                attrs={
                    "placeholder": "Enter an url of a site to check",
                }
            ),
        }


class SubscriptionForm(forms.models.ModelForm):

    class Meta:
        model = Subscription
        exclude = ("site",)