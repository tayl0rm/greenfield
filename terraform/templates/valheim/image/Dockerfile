FROM debian

# Install SteamCMD
RUN apt update && \
    apt install -y curl wget zip unzip libatomic1 libpulse-dev libpulse0
RUN mkdir ~/Steam && cd ~/Steam
RUN curl -sqL "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" | tar zxvf -

#Run Server as Daemon
COPY scripts/valheim.sh /etc/init.d
RUN chmod u+x /etc/init.d/valheim.sh && \
    update-rc.d valheim.sh defaults

