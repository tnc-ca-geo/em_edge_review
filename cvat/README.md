# Computer Vision Annotation Tool (CVAT)

This project uses CVAT for video annotation. For more information about CVAT, please visit the [official website](https://github.com/cvat-ai/cvat).

## Installation

To install CVAT, please follow the instructions in the [official documentation](https://docs.cvat.ai/docs/administration/basics/installation/)
or use the following custom instructions:

1. Install [Docker](https://docs.cvat.ai/docs/administration/basics/installation/).

2. Create a `.env` file in this directory with the following content:

```bash
# CVAT
CVAT_VERSION=v2.22.0
CVAT_HOST=localhost

# Postgresql
CVAT_POSTGRES_USER=root
CVAT_POSTGRES_DBNAME=cvat
CVAT_POSTGRES_PASSWORD=secure_password

# Traefik
TRAEFIK_PORT_1=8183 # 8080
TRAEFIK_PORT_2=8193 # 8090

# Mounted directory
CVAT_COMPONENTS_DIR=/path/to/cvat/cvat_components
CVAT_SHARE_DIR=/path/to/shared/folder/containing/data

# Misc
CVAT_SERVERLESS=1 # 0 - disable, 1 - enable
CVAT_NUCLIO_HOST=nuclio
CVAT_ANALYTICS=0 # 0 - disable, 1 - enable
CLAM_AV=yes
```

2. Copy a required folder from CVAT repository to the directory defined in the env variable named `CVAT_COMPONENTS_DIR`:

```bash

# Read environment variables:
set -o allexport
source .env
set +o allexport

# Create local directories to persist data if they don't exist
if [[ ! -d "$CVAT_COMPONENTS_DIR" ]]; then
  echo "Creating data directory at $CVAT_COMPONENTS_DIR..."
  mkdir -p "$CVAT_COMPONENTS_DIR"
fi

# Go to the directory where the folder will be copied:
cd $CVAT_COMPONENTS_DIR

# Initialize a new repository and set it up for sparse checkout:
git init
git remote add origin git@github.com:cvat-ai/cvat.git
git config core.sparseCheckout true

# Specify the folder to be copied:
echo "components/" >> .git/info/sparse-checkout

# Pull the folder and checkout by the tag version:
git pull origin tag $CVAT_VERSION
git checkout tags/$CVAT_VERSION

# Remove unused created folder
rm -rf cvat-ui
```

3. Go to `/em_edge_review/cvat` folder and run the following script to deploy CVAT:

```bash
./deploy-cvat.sh
```

4. Create a superuser account and login with this user and password:

```bash
docker exec -it cvat_server bash -ic 'python3 ~/manage.py createsuperuser'
```

## Usage

- Stop CVAT:

```bash
docker compose \
    -f docker-compose.yml \
    down
```

- Check health status of the services:

```bash
docker exec -t cvat_server python manage.py health_check
```

- Remove data directories using `sudo` permissions by spinning up a temporary Alpine container:

```bash
docker run --rm -it \
-v /path/to/dir/containinig/mounted/dirs:/cvat alpine \
sh -c 'rm -rvf /cvat/cvat_db /cvat/cvat_data /cvat/cvat_keys /cvat/cvat_logs /cvat/cvat_inmem_db /cvat/cvat_events_db /cvat/cvat_cache_db'
```

- Copy videos to the shared directory using `sudo` permissions by spinning up a temporary Ubuntu container:

```bash
docker run --rm \
  -v /path/to/videos:/source:ro \
  -v /path/to/cvat-share:/destination \
  alpine \
  cp /source/* /destination/

```