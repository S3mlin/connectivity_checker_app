from django.shortcuts import render, redirect
from .forms import SiteForm, SubscriptionForm
from helper_functions.checker import check_site, process_url
from .models import Site, Subscription
from django.contrib.auth import get_user_model

User = get_user_model()


def home_page(request):
    current_user = request.user
    sites = Site.objects.all()
    if request.method == "POST":
        form = SiteForm(data=request.POST)
        if form.is_valid():
            print("valid")
            host = process_url(form.data["url"])
            test = check_site(host)
            site = Site.objects.filter(url=host)
            print(site)
            if test[0] is None:
                return render(
                    request,
                    "home.html",
                    {
                        "form": form,
                        "sites": sites,
                        "message": test[1],
                        "user": current_user,
                    },
                )
            elif test[0]:
                if site:
                    print('tu')
                    site.update(ping=test[1])
                    return redirect("/")

                obj = form.save(commit=False)
                obj.url = host
                obj.ping = test[1]
                obj.save()
        return redirect("/")
    else:
        form = SiteForm()
    return render(
        request, "home.html", {"form": form, "sites": sites, "user": current_user}
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


def subscribe(request, email, site_id):
    site = Site.objects.get(id=site_id)
    owner = User.objects.get(email=email)
    instance = Subscription.objects.filter(
        site=site, user=owner
    )
    
    if instance:
        return redirect("my_sites", email=owner.email)
    else:
        Subscription.objects.create(site=site, user=owner)
    
    return redirect("my_sites", email=owner.email)


def unsubscribe(request, email, site_id):
    site = Site.objects.get(id=site_id)
    owner = User.objects.get(email=email)
    try:
        instance = Subscription.objects.filter(
            site=site, user=owner
        )
        
        if instance:
            instance.delete()
            return redirect("my_sites", email=owner.email)
        else:
            return redirect("my_sites", email=owner.email)
    except Subscription.DoesNotExist:
        return redirect("my_sites", email=owner.email)
    

def search_and_subscribe(request, email):
    owner = User.objects.get(email=email)
    host = process_url(request.POST.get('url'))
    print(host)
    site = Site.objects.filter(url=host)
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