import requests

r = requests.get("https://puzz.link/db/api/pzvs_anon?limit=10001&order=sort_key.asc&type=in.(%22akari%22)&generated=eq.false&tags_filter=cs.{}&tags_filter=not.cs.{broken}&tags_filter=not.cs.{variant}")
for u in r.json():
    wow = "https://puzz.link/p?" + u["pzv"].replace("lightup/","akari/")
    print(wow)