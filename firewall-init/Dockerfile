FROM alpine:3.24

RUN apk add --no-cache iptables

COPY setup-firewall.sh /usr/local/sbin/setup-firewall
RUN chmod 755 /usr/local/sbin/setup-firewall

ENTRYPOINT ["/usr/local/sbin/setup-firewall"]
