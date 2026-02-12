from django.shortcuts import render, redirect
from .forms import SiteForm, SubscriptionForm
from helper_functions.checker import check_site, process_url
from .models import Site, Subscription
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Case, When, BooleanField

User = get_user_model()


def home_page(request):
    user=request.user
    current_user = request.user
    recent_sites = Site.objects.annotate(
        is_subscribed=Count('subscription', filter=Q(subscription__user=current_user))
    ).annotate(
        is_subscribed_bool=Case(
            When(is_subscribed__gt=0, then=True),
            default=False,
            output_field=BooleanField()
        )
    ).order_by("-date_modified")[:5]
    top_sites = Site.objects.annotate(
        num_subscriptions=Count('subscription'),
        is_subscribed=Count('subscription', filter=Q(subscription__user=current_user))
    ).annotate(
        is_subscribed_bool=Case(
            When(is_subscribed__gt=0, then=True),
            default=False,
            output_field=BooleanField()
        )
    ).order_by('-num_subscriptions')[:5]
    if request.method == "POST":
        form = SiteForm(data=request.POST)
        if form.is_valid():
            print("valid")
            host = process_url(form.data["url"])
            test = check_site(host)
            site = Site.objects.filter(url=host).first()
            print(site)
            if test[0] is None:
                return render(
                    request,
                    "home.html",
                    {
                        "form": form,
                        "recent_sites": recent_sites,
                        "top_sites": top_sites,
                        "message": test[1],
                        "user": current_user,
                    },
                )
            elif test[0]:
                if site:
                    print('tu')
                    site.ping = test[1]
                    site.save()
                    return redirect("/")

                obj = form.save(commit=False)
                obj.url = host
                obj.ping = test[1]
                obj.save()
        return render(
                    request,
                    "home.html",
                    {
                        "form": form,
                        "recent_sites": recent_sites,
                        "top_sites": top_sites,
                        "user": current_user,
                    },
                )
    else:
        form = SiteForm()
    return render(
        request, "home.html", {"form": form, "recent_sites": recent_sites, "top_sites": top_sites, "user": current_user}
    )


def my_sites(request, email):
    owner = User.objects.get(email=email)
    subscriptions = Subscription.objects.filter(user=owner)
    if request.method == "POST":
        form = SubscriptionForm(user=request.user)
        if form.is_valid():
            url = form.data["url"]
            test = check_site(url)
            if test[0] is None:
                return render(
                    request,
                    "home.html",
                    {
                        "form": form,
                        "message": test[1],
                        "owner": owner,
                        "subscriptions": subscriptions
                    },
                )
            elif test[0]:
                obj = form.save(commit=False)
                site = Site.objects.get_or_create(
                    url=url, ping=test[1]
                )
                obj.site = site
                obj.save()
    else:
        form = SubscriptionForm()
    return render(request, "my_sites.html", {"form": form, "owner": owner, "subscriptions": subscriptions})


def subscribe(request, email, site_id, last_url):
    site = Site.objects.get(id=site_id)
    owner = User.objects.get(email=email)
    instance = Subscription.objects.filter(
        site=site, user=owner
    )
    
    if last_url == "home":
        last_url = "/"
    
    if instance:
        return redirect(last_url, email=owner.email)
    else:
        Subscription.objects.create(site=site, user=owner)
    
    return redirect(last_url, email=owner.email)


def unsubscribe(request, email, site_id, last_url):
    site = Site.objects.get(id=site_id)
    owner = User.objects.get(email=email)

    if last_url == "home":
        last_url = "/"

    try:
        instance = Subscription.objects.filter(
            site=site, user=owner
        )
        
        if instance:
            instance.delete()
            return redirect(last_url, email=owner.email)
        else:
            return redirect(last_url, email=owner.email)
    except Subscription.DoesNotExist:
        return redirect(last_url, email=owner.email)
    

def search_and_subscribe(request, email):
    owner = User.objects.get(email=email)
    host = process_url(request.POST.get('url'))
    print(host)
    site = Site.objects.filter(url=host).first()
    print(site)
    if site:
        print('vec postoji')
        check_subscription = Subscription.objects.filter(user=owner, site__url=host)

        if check_subscription:
            print('vec subscribean')
            return redirect("my_sites", email=owner.email)
        
        Subscription.objects.create(user=owner, site=site)
        print('subscribean')
        return redirect("my_sites", email=owner.email)

    test = check_site(host)
    if test[0] is None:
        print('site ne postoji')
        return redirect("my_sites", email=owner.email)
    
    elif test[0]:
        print('napravljen site, subscribean')
        site = Site.objects.create(url=host, ping=test[1])
        Subscription.objects.create(user=owner, site=site)
        return redirect("my_sites", email=owner.email)