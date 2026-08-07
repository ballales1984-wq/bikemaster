import urllib.request

r = urllib.request.urlopen('https://bikemaster-xi.vercel.app/sw.js', timeout=10)
content = r.read().decode()

# Look at context around cache:"reload"
pos = 30787
start = max(0, pos - 200)
end = min(len(content), pos + 200)
print("=== Context around cache:reload ===")
print(content[start:end])
print()

# Also search for the navigation handler pattern
pos2 = content.find('navigate')
start2 = max(0, pos2 - 100)
end2 = min(len(content), pos2 + 300)
print("=== Context around 'navigate' ===")
print(content[start2:end2])
