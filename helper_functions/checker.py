import httpx
import asyncio
from tcppinglib import tcpping
from urllib.parse import urlparse
from main_app.models import Site
from asgiref.sync import sync_to_async



def process_url(url):
    if "//" not in url:
        url = "//" + url
    
    parser = urlparse(url)
    return parser.netloc or parser.path.split("/")[0]


def check_site(host):
    try:
        print(host)
        site = tcpping(host, count=5, interval=0.2)
        return site.is_alive, site.avg_rtt
    except:
        message = "The url you entered does not exist!"
        return None, message

async def httpx_check_site(client, url):
    response = await client.get(f"https://{url}")
    return response.elapsed.total_seconds()

@sync_to_async
def get_subscribed_sites():
    return list(Site.objects.filter(subscription__isnull=False).distinct())

@sync_to_async
def update_sites(sites):
    Site.objects.bulk_update(sites, ['ping'])

async def check_subscribed_sites_async():
    sites = await get_subscribed_sites()
    async with httpx.AsyncClient() as client:
        tasks = [httpx_check_site(client, site.url) for site in sites]
        results = await asyncio.gather(*tasks)
    for site, ping in zip(sites, results):
        site.ping = ping
    await update_sites(sites)