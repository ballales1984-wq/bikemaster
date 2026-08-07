import urllib.request

try:
    r = urllib.request.urlopen('https://bikemaster-xi.vercel.app/sw.js', timeout=10)
    content = r.read().decode()
    print('Vercel sw.js size:', len(content))

    patterns = ['cache:"reload"', 'event.request', 'navigationPreload',
                'registerRoute', 'navigate', 'StaleWhileRevalidate']
    for p in patterns:
        idx = content.find(p)
        if idx >= 0:
            print(f'  Found "{p}" at pos {idx}')
        else:
            print(f'  NOT FOUND: "{p}"')

    if 'event.request' in content:
        idx = 0
        count = 0
        while count < 5:
            idx = content.find('event.request', idx)
            if idx == -1:
                break
            snippet = content[max(0, idx-30):idx+50]
            print(f'  event.request at {idx}: ...{snippet}...')
            idx += 1
            count += 1
    else:
        print('  No event.request pattern found')
except Exception as e:
    print('Error:', e)
