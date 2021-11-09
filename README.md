# gw1000-homebridge-http-webhooks
The [homebridge-http-webhooks](https://www.npmjs.com/package/homebridge-http-webhooks "homebridge-http-webhooks")
plugin is an excellent way to create sensors with a nice HTTP API. This daemon
acts as a bridge between
[Ecowitt GW1000](https://www.ecowitt.com/shop/goodsDetail/107 "Ecowitt GW1000")
push notifications and translates them into the API the webhooks plugin
understands. The tool is pure Python 3 and requires no external libraries.
Performing push notifications to Homebridge is efficient and makes the data
immediately available to Homekit clients.

# Installation
Place the `srv.py`and `default.cfg` in the same directory anywhere you'd like.
It can also be run directly from the Git repo.

# Setup the server
By default `srv.py` reads `default.cfg`. You can specify a different config
file with the `-c` argument. All the configuration parameters are explained
in comments inside of `default.cfg`.

# Setup the Ecowitt to push notifications
Using the Ecowitt WS View app on your phone/tablet:

- Pick `menu` -> `Device List` -> select your GW1000
- Use `More` in the top right and select `Weather Services`
- Use `Next` repeatedly to locate the `Customized` server option
- Select `Enable`
- Set `Server IP / Hostname` to the IP address of the host running `srv.py`
- Set `Path` to any value, `srv.py` ignores this information
- Set `Port` to the port specified in `default.cfg` as option `server.port` (default is `10000`)
- Set `Upload Interval` to something reasonable like `60` seconds
- Push the `Save` button

The Ecowitt GW1000 will now send live data information to `srv.py` at the
interval you specified.

# Setup Homebridge
The homebridge-http-webhooks plugin with`HTTP` access no authorization is
required. Currently only the Temperature and Humidity sensor types are
supported. A 1:1 map is necessary between Ecowitt temperature/humidity
device and a webhooks accessory ID name.
