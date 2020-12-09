.PHONY: build push

PLATFORMS = linux/amd64,linux/arm64

build:
	docker build -t mtik00/pysysmon:dev .

push:
	docker buildx build --platform ${PLATFORMS} -t mtik00/pysysmon:latest --push .
