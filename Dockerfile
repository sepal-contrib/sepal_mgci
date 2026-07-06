FROM mambaorg/micromamba:latest

LABEL org.opencontainers.image.source="https://github.com/sepal-contrib/sepal_mgci"

WORKDIR /usr/local/lib/mgci

USER root
# libjemalloc2: allocator for the runtime (see ENV block near the end).
RUN apt-get update && apt-get install -y \
    nano curl neovim supervisor netcat-openbsd net-tools git libjemalloc2 \
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

# Run under jemalloc so freed per-session memory returns to the OS. glibc/pymalloc
# never release the arenas dented by per-session widget churn, so RSS ratchets to
# the peak working set and stays there until restart; jemalloc purges free pages
# on a decay timer, so memory follows users back down.
# NOTE: if the .so is missing, LD_PRELOAD is silently ignored and PYTHONMALLOC=malloc
# is worse than stock — after any image change verify jemalloc is actually loaded:
#   grep -c jemalloc /proc/<app-python-pid>/maps   # >= 1
# Placed after the build layers so image builds don't run under the preload.
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 \
    PYTHONMALLOC=malloc \
    MALLOC_CONF=background_thread:true,dirty_decay_ms:1000,muzzy_decay_ms:1000

EXPOSE 8766

USER root
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]