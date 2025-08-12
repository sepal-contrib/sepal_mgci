FROM continuumio/miniconda3

WORKDIR /usr/local/lib/mgci

# Install nano and curl
RUN apt-get update && apt-get install -y nano curl neovim supervisor netcat-openbsd net-tools

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf


RUN conda init bash && \
    bash -c "source ~/.bashrc && \
    conda create -n sepal_mgci python==3.10 pip -y"

COPY requirements.txt /usr/local/lib/mgci/requirements.txt

RUN bash -c "source ~/.bashrc && conda activate sepal_mgci && pip install -r requirements.txt --no-cache-dir"

COPY . /usr/local/lib/mgci

EXPOSE 8766

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]