#!/bin/sh
set -eu

while [ ! -s /run/firewall/token ]; do
  sleep 0.1
done

token="$(cat /run/firewall/token)"

iptables -I OUTPUT 1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -I OUTPUT 2 -d 172.21.0.2 -j REJECT

printf '%s' "$token" > /run/firewall/ready
