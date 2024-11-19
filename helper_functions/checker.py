from urllib.parse import urlparse
from tcppinglib import tcpping


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
