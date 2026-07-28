FROM rustfs/rustfs:latest
USER root
RUN addgroup -g 5000 secrets \
    && addgroup rustfs secrets
USER rustfs