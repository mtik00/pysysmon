FROM python:3.8-buster as compile

# Build our app inside a virtual environment so we can copy
# it out later.

RUN python -m venv --copies /tmp/app-env

WORKDIR /tmp/app-build

COPY ./requirements.txt .

ENV PATH=/tmp/app-env/bin:$PATH

RUN python -m pip install --no-compile --upgrade pip wheel
RUN python -m pip install --no-compile -r requirements.txt && \
    find . -name "*.py[co]" -o -name __pycache__ -exec rm -rf {} +

# Make the virtual env portable
RUN sed -i '40s/.*/VIRTUAL_ENV="$(cd "$(dirname "$(dirname "${BASH_SOURCE[0]}" )")" \&\& pwd)"/' /tmp/app-env/bin/activate
RUN sed -i '1s|.*|#!/usr/bin/env python|' /tmp/app-env/bin/pip*
RUN sed -i '1s/.*python$/#!\/usr\/bin\/env python/' /tmp/app-env/bin/*

# Stuff to help debug
# RUN apt-get update && apt-get install -y vim wget curl dnsutils && \
#     echo "alias ll='ls -alh'" >> /root/.bashrc

###############################################################################
FROM python:3.8-slim-buster

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/src/app/.venv/bin:$PATH" \
    INSTANCE_FOLDER="/usr/src/app/instance"

LABEL maintainer="Timothy McFadden <mtik00@users.noreply.github.com>"
LABEL app="pythnon-sysmon"

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y tini \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash sysmon-user \
    && echo "alias ll='ls -alh'" >> /home/sysmon-user/.bashrc \
    && echo 'PATH="/usr/src/app/.venv/bin:$PATH"' >> /home/sysmon-user/.bashrc

WORKDIR /usr/src/app

COPY --from=compile --chown=sysmon-user:sysmon-user /tmp/app-env .venv
COPY --chown=sysmon-user:sysmon-user ./src/app.py ./app.py

ENTRYPOINT [ "/usr/bin/tini", "--" ]
CMD [ "python", "app.py" ]

# Stuff to help debug
# RUN python -m pip install ipdb

USER sysmon-user
