FROM postgres:16
USER root
RUN groupadd -g 5000 secrets \
    && usermod -aG secrets postgres