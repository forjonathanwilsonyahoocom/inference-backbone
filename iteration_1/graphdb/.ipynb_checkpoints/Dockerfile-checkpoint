# Use the official GraphDB image as base
FROM ontotext/graphdb:7.3.4

# Optional: copy custom configuration if you need to tweak GraphDB settings
# COPY graphdb.conf /opt/graphdb/conf/graphdb.conf

# Expose GraphDB ports (already exposed in docker-compose)
EXPOSE 7200 8080

# Default command starts GraphDB automatically
CMD ["/opt/graphdb/bin/graphdb.sh"]