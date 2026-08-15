FROM google/cloud-sdk:417.0.1-alpine

# Install Tools
RUN apk --no-cache add curl jq coreutils zip python3 && ln -sf python3 /usr/bin/python && \
    python3 -m ensurepip && \
    pip3 install --no-cache --upgrade pip setuptools && \
    mkdir ~/discord_bot

COPY src/bot.py ~/discord_bot/bot.python

RUN python3 -m pip install discord python-dotenv google-api-core google-api-python-client google-cloud-compute
