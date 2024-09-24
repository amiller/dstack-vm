set -ex

# Build with docker
docker build -t app-example:latest app-example

# Store in host_volume/ so we can load it at runtime
docker save -o ./host_volume/app-example.tar app-example:latest
