FROM mambaorg/micromamba:latest

LABEL org.opencontainers.image.source="https://github.com/sepal-contrib/sepal_mgci"

WORKDIR /usr/local/lib/mgci

USER root
RUN apt-get update && apt-get install -y \
    nano curl neovim supervisor netcat-openbsd net-tools git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

USER $MAMBA_USER

COPY requirements.txt /home/$MAMBA_USER/requirements.txt
RUN micromamba create -n sepal_mgci python=3.10 pip -c conda-forge -y && \
    micromamba run -n sepal_mgci pip install -r /home/$MAMBA_USER/requirements.txt --no-cache-dir && \
    micromamba clean --all --yes && \
    rm -f /home/$MAMBA_USER/requirements.txt && \
    rm -rf ~/.cache/pip

COPY . /usr/local/lib/mgci

EXPOSE 8766

USER root
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]