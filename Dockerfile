FROM alpine:3.17
LABEL maintainer="Thomas GUIRRIEC <thomas@guirriec.fr>"
ENV APT_EXPORTER_PORT=8123
ENV APT_EXPORTER_LOGLEVEL='INFO'
ENV APT_EXPORTER_NAME='apt-exporter'
ENV SCRIPT="apt_exporter.py"
ENV USERNAME="exporter"
ENV UID="1000"
COPY apk_packages /
COPY pip_packages /
ENV VIRTUAL_ENV="/apt-exporter"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN xargs -a /apk_packages apk add --no-cache --update \
    && python3 -m venv ${VIRTUAL_ENV} \
    && pip install --no-cache-dir --no-dependencies --no-binary :all: -r pip_packages \
    && pip uninstall -y setuptools pip \
    && useradd -l -u ${UID} -U -s /bin/sh ${USERNAME} \
    && rm -rf \
        /root/.cache \
        /tmp/* \
        /var/cache/*
COPY --chown=${USERNAME}:${USERNAME} --chmod=500 entrypoint.sh /
COPY --chown=${USERNAME}:${USERNAME} --chmod=500 ${SCRIPT} ${VIRTUAL_ENV}
COPY --chown=${USERNAME}:${USERNAME} --chmod=500 dpkg_status /var/lib/dpkg/status
WORKDIR ${VIRTUAL_ENV}
EXPOSE ${APT_EXPORTER_PORT}
USER ${USERNAME}
HEALTHCHECK CMD nc -vz localhost ${APT_EXPORTER_PORT} || exit 1 # nosemgrep
ENTRYPOINT ["/entrypoint.sh"]
