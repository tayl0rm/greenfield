FROM debian

# Install SteamCMD
RUN apt update -y && \
    apt install -y curl wget zip unzip libatomic1 libpulse-dev libpulse0
RUN curl -L -o /tmp/steamcmd_linux.tar.gz https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz \
    && mkdir /opt/steamcmd \
    && tar xzvf /tmp/steamcmd_linux.tar.gz -C /opt/steamcmd/ \
    && chown -R root:root /opt/steamcmd \
    && chmod 755 /opt/steamcmd/steamcmd.sh \
    && cd "/opt/steamcmd" \
    && su - root -c "/opt/steamcmd/steamcmd.sh +login anonymous +app_update 896660 +quit"

#Run Server as Daemon
COPY scripts/valheim.sh /etc/init.d
RUN chmod u+x /etc/init.d/valheim.sh && \
    update-rc.d valheim.sh defaults
