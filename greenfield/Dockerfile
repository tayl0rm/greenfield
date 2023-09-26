FROM google/cloud-sdk:417.0.1-alpine

#################
# Install Tools #
#################

RUN wget https://releases.hashicorp.com/terraform/0.13.7/terraform_0.13.7_linux_amd64.zip && \
    unzip terraform_0.13.7_linux_amd64.zip -d /usr/local/bin/ && \
    rm -rf terraform_0.13.7_linux_amd64.zip && \
    apk --no-cache add curl jq coreutils zip python3 && ln -sf python3 /usr/bin/python && \
    python3 -m ensurepip && \
    pip3 install --no-cache --upgrade pip setuptools && \
    mkdir discord_bot

COPY bot.py discord_bot/bot.python

RUN python3 -m pip install discord python-dotenv google-api-core google-api-python-client google-cloud-compute
