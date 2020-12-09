.PHONY: build

PLATFORMS = linux/amd64,linux/arm64

push:
	docker buildx build --platform ${PLATFORMS} -t mtik00/pysysmon:latest --push .
